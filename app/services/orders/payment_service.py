from typing import Any, Dict

import mysql.connector

from app.core.db import get_db_connection
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
    )
from app.exceptions.service_exceptions import (
    InvalidOperationError, OutOfStockError, 
    PaymentFailedError, ServiceLogicError
    )
from app.services.orders.stock_service import stock_service
from app.services.products.variant_service import variant_service
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class PaymentService:

    def process_successful_payment(
        self, transaction_id: str
    ) -> Dict[str, Any]:
        logger.info(
            f"Memproses webhook pembayaran sukses untuk transaction_id: {transaction_id}"
        )

        conn = None
        cursor = None
        order = None
        order_id = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "SELECT id, status, payment_method, user_id FROM orders WHERE payment_transaction_id = %s",
                (transaction_id,),
            )

            order = cursor.fetchone()

            if not order:
                logger.warning(
                    f"Webhook pembayaran gagal: Pesanan dengan transaction_id {transaction_id} tidak ditemukan."
                )
                raise RecordNotFoundError(
                    f"Pesanan dengan transaction_id {transaction_id} tidak ditemukan."
                )
            
            order_id = order["id"]

            if order["status"] != "Menunggu Pembayaran":
                logger.info(
                    f"Webhook pembayaran dilewati untuk pesanan {order_id}: "
                    f"Statusnya '{order['status']}', bukan 'Menunggu Pembayaran'."
                )
                return {
                    "success": True,
                    "message": "Pesanan sudah diproses sebelumnya atau dibatalkan.",
                }
            
            logger.debug(f"Mengambil item untuk pesanan {order_id}")

            cursor.execute(
                "SELECT * FROM order_items WHERE order_id = %s", (order_id,)
            )

            items = cursor.fetchall()

            logger.debug(
                f"Memulai logika pemrosesan pembayaran pesanan {order_id} (tanpa start_transaction eksplisit)."
            )

            stock_sufficient = True
            failed_item_info = ""

            for item in items:
                available_stock = stock_service.get_available_stock(
                    item["product_id"], item["variant_id"], conn
                )
                logger.debug(
                    f"Memeriksa stok untuk item di pesanan {order_id}: "
                    f"Produk {item['product_id']}, Varian {item['variant_id']}, "
                    f"Diperlukan {item['quantity']}, Tersedia {available_stock}"
                )

                if item["quantity"] > available_stock:
                    stock_sufficient = False

                    cursor.execute(
                        "SELECT name FROM products WHERE id = %s",
                        (item["product_id"],),
                    )

                    product_info = cursor.fetchone()

                    product_name = (
                        product_info["name"]
                        if product_info
                        else f"ID {item['product_id']}"
                    )

                    size_info = ""

                    if item["variant_id"]:

                        cursor.execute(
                            "SELECT size FROM product_variants WHERE id = %s",
                            (item["variant_id"],),
                        )

                        variant_info = cursor.fetchone()

                        if variant_info:
                            size_info = f" (Ukuran: {variant_info['size']})"

                    failed_item_info = (
                        f"'{product_name}'{size_info}. Diminta: {item['quantity']}, "
                        f"Tersedia: {available_stock}"
                    )
                    logger.error(
                        f"Stok tidak mencukupi untuk pesanan {order_id}, {failed_item_info}"
                    )
                    break

            if not stock_sufficient:
                logger.warning(
                    f"Membatalkan pesanan {order_id} karena stok tidak mencukupi saat konfirmasi pembayaran."
                )

                cursor.execute(
                    "UPDATE orders SET status = 'Dibatalkan', notes = %s WHERE id = %s",
                    (
                        "Dibatalkan otomatis karena stok habis saat pembayaran dikonfirmasi.",
                        order_id,
                    ),
                )
                cursor.execute(
                    "INSERT INTO order_status_history (order_id, status, notes) VALUES (%s, %s, %s)",
                    (
                        order_id,
                        "Dibatalkan",
                        "Dibatalkan otomatis karena stok habis saat pembayaran dikonfirmasi.",
                    ),
                )

                stock_service.release_stock_holds(
                    order.get("user_id"), None, conn
                )
                logger.info(
                    f"Melepaskan penahanan stok (jika ada) untuk pesanan {order_id} karena pembatalan."
                )

                conn.commit()

                return {
                    "success": False,
                    "message": f"Pembayaran gagal karena stok habis untuk {failed_item_info}.",
                }
            
            logger.debug(f"Mengurangi stok untuk pesanan {order_id}")
            product_ids_with_variants = set()

            for item in items:
                lock_query = (
                    "SELECT stock FROM product_variants WHERE id = %s FOR UPDATE"
                    if item["variant_id"]
                    else "SELECT stock FROM products WHERE id = %s FOR UPDATE"
                )
                lock_id = (
                    item["variant_id"]
                    if item["variant_id"]
                    else item["product_id"]
                )

                cursor.execute(lock_query, (lock_id,))
                current_stock_row = cursor.fetchone()

                if (
                    not current_stock_row
                    or current_stock_row["stock"] < item["quantity"]
                ):
                    conn.rollback()

                    failed_item_info = f"item ID {'variant ' + str(lock_id) if item['variant_id'] else str(lock_id)}"
                    logger.error(
                        f"Stok habis saat mencoba mengurangi untuk {failed_item_info} di pesanan {order_id}"
                    )

                    conn_cancel = get_db_connection()
                    cursor_cancel = conn_cancel.cursor()

                    try:
                        cursor_cancel.execute(
                            "UPDATE orders SET status = 'Dibatalkan', notes = %s WHERE id = %s",
                            (
                                f"Dibatalkan otomatis karena stok habis ({failed_item_info}) saat konfirmasi pembayaran.",
                                order_id,
                            ),
                        )
                        cursor_cancel.execute(
                            "INSERT INTO order_status_history (order_id, status, notes) VALUES (%s, %s, %s)",
                            (
                                order_id,
                                "Dibatalkan",
                                f"Dibatalkan otomatis karena stok habis ({failed_item_info}) saat konfirmasi pembayaran.",
                            ),
                        )

                        conn_cancel.commit()

                        logger.warning(
                            f"Pesanan {order_id} dibatalkan karena stok habis saat transaksi pengurangan."
                        )

                    except Exception as cancel_err:
                        logger.error(
                            f"Gagal membatalkan pesanan {order_id} setelah rollback: {cancel_err}",
                            exc_info=True,
                        )

                        if conn_cancel and conn_cancel.is_connected():
                            conn_cancel.rollback()

                    finally:
                        if cursor_cancel:
                            cursor_cancel.close()
                        if conn_cancel and conn_cancel.is_connected():
                            conn_cancel.close()

                    return {
                        "success": False,
                        "message": f"Pembayaran gagal karena stok habis untuk {failed_item_info}.",
                    }
                
                update_query = (
                    "UPDATE {} SET stock = stock - %s WHERE id = %s"
                ).format(
                    "product_variants" if item["variant_id"] else "products"
                )

                cursor.execute(update_query, (item["quantity"], lock_id))

                if cursor.rowcount == 0:
                    conn.rollback()
                    err_msg = (
                        f"Gagal mengurangi stok (rowcount 0) untuk "
                        f"{'varian' if item['variant_id'] else 'produk'} ID {lock_id}"
                    )
                    logger.error(err_msg)
                    raise ServiceLogicError(err_msg)
                
                if item["variant_id"]:
                    product_ids_with_variants.add(item["product_id"])

            logger.info(f"Stok berhasil dikurangi untuk pesanan {order_id}")
            logger.debug(
                f"Memperbarui status pesanan menjadi 'Diproses' untuk pesanan {order_id}"
            )

            cursor.execute(
                "UPDATE orders SET status = 'Diproses' WHERE id = %s", (order_id,)
            )
            history_notes = (
                f'Pembayaran via {order["payment_method"]} berhasil dikonfirmasi.'
            )

            cursor.execute(
                "INSERT INTO order_status_history (order_id, status, notes) VALUES (%s, %s, %s)",
                (order_id, "Diproses", history_notes),
            )

            stock_service.release_stock_holds(order.get("user_id"), None, conn)
            logger.info(
                f"Melepaskan penahanan stok untuk pesanan {order_id} yang berhasil diproses."
            )

            conn.commit()
            logger.info(
                f"Transaksi pemrosesan pembayaran di-commit untuk pesanan {order_id}."
            )

            if product_ids_with_variants:
                logger.debug(
                    f"Memperbarui total stok produk untuk produk dengan varian: "
                    f"{product_ids_with_variants}"
                )
                temp_conn_for_variant = None

                try:
                    temp_conn_for_variant = get_db_connection()
                    for pid in product_ids_with_variants:
                        variant_service.update_total_stock_from_variants(
                            pid, temp_conn_for_variant
                        )
                        temp_conn_for_variant.commit()
                    logger.info("Total stok produk diperbarui.")

                except Exception as variant_err:
                    logger.error(
                        f"Kesalahan saat memperbarui total stok dari varian setelah konfirmasi pembayaran "
                        f"untuk pesanan {order_id}: {variant_err}",
                        exc_info=True,
                    )

                finally:
                    if (
                        temp_conn_for_variant
                        and temp_conn_for_variant.is_connected()
                    ):
                        temp_conn_for_variant.close()

            logger.info(
                f"Pembayaran berhasil diproses untuk transaksi {transaction_id}, "
                f"ID Pesanan {order_id}. Status diatur ke 'Diproses'."
            )

            return {
                "success": True,
                "message": f"Pesanan #{order_id} berhasil diproses.",
            }

        except (mysql.connector.Error, DatabaseException) as e:
            if conn and conn.is_connected():

                try:
                    conn.rollback()
                    logger.info(
                        f"Transaksi di-rollback karena error database pada pesanan {order_id}."
                    )

                except Exception as rb_err:
                    logger.error(
                        f"Gagal melakukan rollback setelah error database: {rb_err}",
                        exc_info=True,
                    )

            logger.error(
                f"Kesalahan database selama pemrosesan pembayaran untuk transaksi {transaction_id}, "
                f"ID Pesanan {order_id}: {e}",
                exc_info=True,
            )

            if isinstance(e, RecordNotFoundError):
                return {"success": False, "message": str(e)}
            
            return {
                "success": False,
                "message": f"Kesalahan database saat memproses pembayaran: {e}",
            }

        except (
            OutOfStockError,
            ServiceLogicError,
            PaymentFailedError,
            InvalidOperationError,
        ) as service_err:
            if conn and conn.is_connected():

                try:
                    conn.rollback()
                    logger.info(
                        f"Transaksi di-rollback karena error service/logika pada pesanan {order_id}: {service_err}"
                    )

                except Exception as rb_err:
                    logger.error(
                        f"Gagal melakukan rollback setelah error service/logika: {rb_err}",
                        exc_info=True,
                    )

            logger.error(
                f"Error service/logika saat pemrosesan pembayaran {transaction_id}: {service_err}",
                exc_info=False,
            )

            return {"success": False, "message": str(service_err)}

        except Exception as e:
            if conn and conn.is_connected():

                try:
                    conn.rollback()
                    logger.info(
                        f"Transaksi di-rollback karena error tak terduga pada pesanan {order_id}."
                    )

                except Exception as rb_err:
                    logger.error(
                        f"Gagal melakukan rollback setelah error tak terduga: {rb_err}",
                        exc_info=True,
                    )

            logger.error(
                f"Kesalahan tak terduga saat memproses webhook pembayaran untuk transaction_id {transaction_id}, "
                f"ID Pesanan {order_id}: {e}",
                exc_info=True,
            )

            return {
                "success": False,
                "message": "Gagal memproses pembayaran: Kesalahan server internal.",
            }

        finally:
            if cursor:
                cursor.close()

            if conn and conn.is_connected():

                try:
                    if conn.in_transaction:
                        logger.warning(
                            f"Transaksi masih aktif saat menutup koneksi untuk pesanan {order_id}. Melakukan rollback paksa."
                        )
                        conn.rollback()

                except Exception as final_rb_err:
                    logger.error(
                        f"Error saat final check/rollback koneksi: {final_rb_err}",
                        exc_info=True,
                    )

                finally:
                    conn.close()
                    
            logger.debug(
                f"Koneksi database ditutup untuk process_successful_payment "
                f"(Transaksi {transaction_id})."
            )

payment_service = PaymentService()