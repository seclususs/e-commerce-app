from typing import Any, Dict, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.core.db import get_db_connection
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
)
from app.exceptions.service_exceptions import (
    InvalidOperationError, OutOfStockError,
    PaymentFailedError, ServiceLogicError
)
from app.repository.order_item_repository import (
    OrderItemRepository, order_item_repository
)
from app.repository.order_repository import OrderRepository, order_repository
from app.repository.order_status_history_repository import (
    OrderStatusHistoryRepository, order_status_history_repository
)
from app.repository.product_repository import (
    ProductRepository, product_repository
)
from app.repository.variant_repository import (
    VariantRepository, variant_repository
)
from app.services.orders.stock_service import StockService, stock_service
from app.services.products.variant_service import (
    VariantService, variant_service
)
from app.utils.logging_utils import get_logger


logger = get_logger(__name__)


class PaymentService:

    def __init__(
        self,
        order_repo: OrderRepository = order_repository,
        item_repo: OrderItemRepository = order_item_repository,
        history_repo: OrderStatusHistoryRepository = (
            order_status_history_repository
        ),
        product_repo: ProductRepository = product_repository,
        variant_repo: VariantRepository = variant_repository,
        stock_svc: StockService = stock_service,
        variant_svc: VariantService = variant_service,
    ):
        self.order_repository = order_repo
        self.item_repository = item_repo
        self.history_repository = history_repo
        self.product_repository = product_repo
        self.variant_repository = variant_repo
        self.stock_service = stock_svc
        self.variant_service = variant_svc


    def process_successful_payment(
        self, transaction_id: str
    ) -> Dict[str, Any]:
        
        logger.info(
            "Memproses webhook pembayaran sukses untuk "
            f"transaction_id: {transaction_id}"
        )
        conn: Optional[MySQLConnection] = None
        order = None
        order_id = None

        try:
            conn = get_db_connection()
            order = self.order_repository.find_by_transaction_id(
                conn, transaction_id
            )
            if not order:
                logger.warning(
                    "Webhook pembayaran gagal: Pesanan dengan "
                    f"transaction_id {transaction_id} tidak ditemukan."
                )
                raise RecordNotFoundError(
                    f"Pesanan dengan transaction_id {transaction_id} "
                    "tidak ditemukan."
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
            items = self.item_repository.find_by_order_id(conn, order_id)
            logger.debug(
                f"Memulai logika pemrosesan pembayaran pesanan {order_id} "
                "(tanpa start_transaction eksplisit)."
            )
            stock_sufficient = True
            failed_item_info = ""

            for item in items:
                available_stock = self.stock_service.get_available_stock(
                    item["product_id"], item["variant_id"], conn
                )
                logger.debug(
                    f"Memeriksa stok untuk item di pesanan {order_id}: "
                    f"Produk {item['product_id']}, Varian {item['variant_id']}, "
                    f"Diperlukan {item['quantity']}, Tersedia {available_stock}"
                )
                
                if item["quantity"] > available_stock:
                    stock_sufficient = False
                    product_info = self.product_repository.find_minimal_by_id(
                        conn, item["product_id"]
                    )
                    product_name = (
                        product_info["name"]
                        if product_info
                        else f"ID {item['product_id']}"
                    )
                    size_info = ""

                    if item["variant_id"]:
                        variant_info = self.variant_repository.find_by_id(
                            conn, item["variant_id"]
                        )
                        if variant_info:
                            size_info = f" (Ukuran: {variant_info['size']})"

                    failed_item_info = (
                        f"'{product_name}'{size_info}. Diminta: {item['quantity']}, "
                        f"Tersedia: {available_stock}"
                    )
                    logger.error(
                        f"Stok tidak mencukupi untuk pesanan {order_id}, "
                        f"{failed_item_info}"
                    )
                    break

            if not stock_sufficient:
                logger.warning(
                    f"Membatalkan pesanan {order_id} karena stok tidak "
                    "mencukupi saat konfirmasi pembayaran."
                )
                notes = "Dibatalkan otomatis karena stok habis saat pembayaran dikonfirmasi."
                self.order_repository.update_status_and_notes(
                    conn, order_id, "Dibatalkan", notes
                )
                self.history_repository.create(
                    conn, order_id, "Dibatalkan", notes
                )
                self.stock_service.release_stock_holds(
                    order.get("user_id"), None, conn
                )
                logger.info(
                    "Melepaskan penahanan stok (jika ada) untuk "
                    f"pesanan {order_id} karena pembatalan."
                )
                conn.commit()
                return {
                    "success": False,
                    "message": f"Pembayaran gagal karena stok habis "
                    f"untuk {failed_item_info}.",
                }

            logger.debug(f"Mengurangi stok untuk pesanan {order_id}")
            product_ids_with_variants = set()

            for item in items:
                if item["variant_id"]:
                    lock_id = item["variant_id"]
                    current_stock_row = self.variant_repository.lock_stock(
                        conn, lock_id
                    )
                else:
                    lock_id = item["product_id"]
                    current_stock_row = self.product_repository.lock_stock(
                        conn, lock_id
                    )
                
                if (
                    not current_stock_row
                    or current_stock_row["stock"] < item["quantity"]
                ):
                    conn.rollback()
                    failed_item_info = f"item ID {'variant ' + str(lock_id) if item['variant_id'] else str(lock_id)}"
                    logger.error(
                        "Stok habis saat mencoba mengurangi untuk "
                        f"{failed_item_info} di pesanan {order_id}"
                    )
                    self._cancel_order_due_to_stock_failure(
                        order_id, failed_item_info
                    )
                    return {
                        "success": False,
                        "message": f"Pembayaran gagal karena stok habis "
                        f"untuk {failed_item_info}.",
                    }

                if item["variant_id"]:
                    rowcount = self.variant_repository.decrease_stock(
                        conn, lock_id, item["quantity"]
                    )
                else:
                    rowcount = self.product_repository.decrease_stock(
                        conn, lock_id, item["quantity"]
                    )
                
                if rowcount == 0:
                    conn.rollback()
                    err_msg = (
                        f"Gagal mengurangi stok (rowcount 0) untuk "
                        f"{'varian' if item['variant_id'] else 'produk'} "
                        f"ID {lock_id}"
                    )
                    logger.error(err_msg)
                    raise ServiceLogicError(err_msg)
                
                if item["variant_id"]:
                    product_ids_with_variants.add(item["product_id"])

            logger.info(f"Stok berhasil dikurangi untuk pesanan {order_id}")
            logger.debug(
                "Memperbarui status pesanan menjadi 'Diproses' untuk "
                f"pesanan {order_id}"
            )
            self.order_repository.update_status(conn, order_id, "Diproses")
            history_notes = (
                f'Pembayaran via {order["payment_method"]} berhasil '
                "dikonfirmasi."
            )
            self.history_repository.create(
                conn, order_id, "Diproses", history_notes
            )
            self.stock_service.release_stock_holds(
                order.get("user_id"), None, conn
            )
            logger.info(
                "Melepaskan penahanan stok untuk pesanan {order_id} "
                "yang berhasil diproses."
            )
            conn.commit()

            logger.info(
                "Transaksi pemrosesan pembayaran di-commit untuk "
                f"pesanan {order_id}."
            )
            if product_ids_with_variants:
                self._update_variant_parent_stock(
                    product_ids_with_variants, order_id
                )
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
                        "Transaksi di-rollback karena error database "
                        f"pada pesanan {order_id}."
                    )
                except Exception as rb_err:
                    logger.error(
                        f"Gagal melakukan rollback setelah error database: {rb_err}",
                        exc_info=True,
                    )

            logger.error(
                "Kesalahan database selama pemrosesan pembayaran untuk "
                f"transaksi {transaction_id}, ID Pesanan {order_id}: {e}",
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
            InvalidOperationError
        ) as service_err:
            if conn and conn.is_connected():
                try:
                    conn.rollback()
                    logger.info(
                        "Transaksi di-rollback karena error service/logika "
                        f"pada pesanan {order_id}: {service_err}"
                    )
                except Exception as rb_err:
                    logger.error(
                        "Gagal melakukan rollback setelah error "
                        f"service/logika: {rb_err}",
                        exc_info=True,
                    )
            logger.error(
                "Error service/logika saat pemrosesan pembayaran "
                f"{transaction_id}: {service_err}",
                exc_info=False,
            )
            return {"success": False, "message": str(service_err)}
        
        except Exception as e:
            if conn and conn.is_connected():
                try:
                    conn.rollback()
                    logger.info(
                        "Transaksi di-rollback karena error tak terduga "
                        f"pada pesanan {order_id}."
                    )
                except Exception as rb_err:
                    logger.error(
                        f"Gagal melakukan rollback setelah error tak terduga: {rb_err}",
                        exc_info=True,
                    )
            logger.error(
                "Kesalahan tak terduga saat memproses webhook pembayaran "
                f"untuk transaction_id {transaction_id}, "
                f"ID Pesanan {order_id}: {e}",
                exc_info=True,
            )
            return {
                "success": False,
                "message": "Gagal memproses pembayaran: Kesalahan server internal.",
            }
        
        finally:
            self._close_connection(conn, order_id, transaction_id)


    def _cancel_order_due_to_stock_failure(
        self, order_id: int, failed_item_info: str
    ):
        
        conn_cancel: Optional[MySQLConnection] = None
        try:
            conn_cancel = get_db_connection()
            notes = (
                f"Dibatalkan otomatis karena stok habis "
                f"({failed_item_info}) saat konfirmasi pembayaran."
            )
            self.order_repository.update_status_and_notes(
                conn_cancel, order_id, "Dibatalkan", notes
            )
            self.history_repository.create(
                conn_cancel, order_id, "Dibatalkan", notes
            )
            conn_cancel.commit()
            logger.warning(
                f"Pesanan {order_id} dibatalkan karena stok habis "
                "saat transaksi pengurangan."
            )

        except Exception as cancel_err:
            logger.error(
                f"Gagal membatalkan pesanan {order_id} setelah rollback: {cancel_err}",
                exc_info=True,
            )
            if conn_cancel and conn_cancel.is_connected():
                conn_cancel.rollback()

        finally:
            if conn_cancel and conn_cancel.is_connected():
                conn_cancel.close()


    def _update_variant_parent_stock(
        self, product_ids_with_variants: set, order_id: int
    ):
        
        logger.debug(
            "Memperbarui total stok produk untuk produk dengan varian: "
            f"{product_ids_with_variants}"
        )
        temp_conn_for_variant: Optional[MySQLConnection] = None
        try:
            temp_conn_for_variant = get_db_connection()
            for pid in product_ids_with_variants:
                self.variant_service.update_total_stock_from_variants(
                    pid, temp_conn_for_variant
                )
                temp_conn_for_variant.commit()
            logger.info("Total stok produk diperbarui.")

        except Exception as variant_err:
            logger.error(
                "Kesalahan saat memperbarui total stok dari varian "
                f"setelah konfirmasi pembayaran untuk pesanan {order_id}: "
                f"{variant_err}",
                exc_info=True,
            )

        finally:
            if (
                temp_conn_for_variant
                and temp_conn_for_variant.is_connected()
            ):
                temp_conn_for_variant.close()


    def _close_connection(
        self,
        conn: Optional[MySQLConnection],
        order_id: Optional[int],
        transaction_id: str,
    ):
        
        if conn and conn.is_connected():
            try:
                if conn.in_transaction:
                    logger.warning(
                        "Transaksi masih aktif saat menutup koneksi "
                        f"untuk pesanan {order_id}. Melakukan rollback paksa."
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
            "Koneksi database ditutup untuk process_successful_payment "
            f"(Transaksi {transaction_id})."
        )

payment_service = PaymentService(
    order_repository, order_item_repository, order_status_history_repository,
    product_repository, variant_repository, stock_service, variant_service
)