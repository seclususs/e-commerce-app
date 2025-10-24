import mysql.connector
from app.core.db import get_db_connection
from app.services.orders.stock_service import stock_service
from app.services.products.variant_service import variant_service
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class PaymentService:


    def process_successful_payment(self, transaction_id):
        logger.info(f"Memproses webhook pembayaran sukses untuk transaction_id: {transaction_id}")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        order = None
        order_id = None

        try:
            cursor.execute(
                "SELECT id, status, payment_method, user_id FROM orders WHERE payment_transaction_id = %s",
                (transaction_id,)
            )
            order = cursor.fetchone()

            if not order:
                logger.warning(f"Webhook pembayaran gagal: Pesanan dengan transaction_id {transaction_id} tidak ditemukan.")
                return {'success': False, 'message': 'Pesanan tidak ditemukan.'}

            order_id = order['id']

            if order['status'] != 'Menunggu Pembayaran':
                logger.info(
                    f"Webhook pembayaran dilewati untuk pesanan {order_id}: "
                    f"Statusnya '{order['status']}', bukan 'Menunggu Pembayaran'."
                )
                return {'success': True, 'message': 'Pesanan sudah diproses sebelumnya atau dibatalkan.'}

            logger.debug(f"Mengambil item untuk pesanan {order_id}")
            cursor.execute("SELECT * FROM order_items WHERE order_id = %s", (order_id,))
            items = cursor.fetchall()

            conn.start_transaction()
            logger.debug(f"Memulai transaksi untuk pemrosesan pembayaran pesanan {order_id}.")

            stock_sufficient = True
            failed_item_info = ""

            for item in items:
                available_stock = stock_service.get_available_stock(
                    item['product_id'], item['variant_id'], conn
                )
                logger.debug(
                    f"Memeriksa stok untuk item di pesanan {order_id}: "
                    f"Produk {item['product_id']}, Varian {item['variant_id']}, "
                    f"Diperlukan {item['quantity']}, Tersedia {available_stock}"
                )

                if item['quantity'] > available_stock:
                    stock_sufficient = False

                    product_name_info = f"Produk ID {item['product_id']}"
                    if item['variant_id']:
                        cursor.execute("SELECT size FROM product_variants WHERE id = %s", (item['variant_id'],))
                        variant_info = cursor.fetchone()
                        if variant_info:
                            product_name_info += f" (Ukuran: {variant_info['size']})"

                    failed_item_info = (
                        f"item {product_name_info}. Diminta: {item['quantity']}, "
                        f"Tersedia: {available_stock}"
                    )

                    logger.error(f"Stok tidak mencukupi untuk pesanan {order_id}, {failed_item_info}")
                    break

            if not stock_sufficient:
                logger.warning(
                    f"Membatalkan pesanan {order_id} karena stok tidak mencukupi saat konfirmasi pembayaran."
                )
                cancel_notes = (
                    'Dibatalkan otomatis karena stok habis saat pembayaran dikonfirmasi.'
                )
                cursor.execute(
                    "UPDATE orders SET status = 'Dibatalkan', notes = %s WHERE id = %s",
                    (cancel_notes, order_id)
                )
                cursor.execute(
                    "INSERT INTO order_status_history (order_id, status, notes) VALUES (%s, %s, %s)",
                    (order_id, 'Dibatalkan', cancel_notes)
                )
                stock_service.release_stock_holds(order.get('user_id'), None, conn)
                logger.info(
                    f"Melepaskan penahanan stok untuk pesanan {order_id} karena pembatalan."
                )
                conn.commit()
                return {
                    'success': False,
                    'message': f"Pembayaran gagal diproses karena stok habis untuk {failed_item_info}."
                }

            logger.debug(f"Mengurangi stok untuk pesanan {order_id}")
            product_ids_with_variants = set()

            for item in items:
                update_query = (
                    "UPDATE {} SET stock = stock - %s WHERE id = %s"
                ).format("product_variants" if item['variant_id'] else "products")

                update_id = item['variant_id'] if item['variant_id'] else item['product_id']

                cursor.execute(update_query, (item['quantity'], update_id))

                if cursor.rowcount == 0:
                    err_msg = (
                        f"Gagal mengurangi stok untuk "
                        f"{'varian' if item['variant_id'] else 'produk'} ID {update_id}"
                    )
                    logger.error(err_msg)
                    raise Exception(err_msg)

                if item['variant_id']:
                    product_ids_with_variants.add(item['product_id'])

            logger.info(f"Stok berhasil dikurangi untuk pesanan {order_id}")

            logger.debug(f"Memperbarui status pesanan menjadi 'Diproses' untuk pesanan {order_id}")
            cursor.execute("UPDATE orders SET status = 'Diproses' WHERE id = %s", (order_id,))

            history_notes = f'Pembayaran via {order["payment_method"]} berhasil dikonfirmasi.'
            cursor.execute(
                "INSERT INTO order_status_history (order_id, status, notes) VALUES (%s, %s, %s)",
                (order_id, 'Diproses', history_notes)
            )

            stock_service.release_stock_holds(order.get('user_id'), None, conn)
            logger.info(f"Melepaskan penahanan stok untuk pesanan {order_id} yang berhasil diproses.")

            conn.commit()
            logger.info(f"Transaksi pemrosesan pembayaran di-commit untuk pesanan {order_id}.")

            if product_ids_with_variants:
                logger.debug(
                    f"Memperbarui total stok produk untuk produk dengan varian: "
                    f"{product_ids_with_variants}"
                )
                temp_conn_for_variant = get_db_connection()

                try:
                    for pid in product_ids_with_variants:
                        variant_service.update_total_stock_from_variants(pid)
                    logger.info("Total stok produk diperbarui.")
                except Exception as variant_err:
                    logger.error(
                        f"Kesalahan saat memperbarui total stok dari varian setelah konfirmasi pembayaran "
                        f"untuk pesanan {order_id}: {variant_err}",
                        exc_info=True
                    )
                finally:
                    temp_conn_for_variant.close()

            logger.info(
                f"Pembayaran berhasil diproses untuk transaksi {transaction_id}, "
                f"ID Pesanan {order_id}. Status diatur ke 'Diproses'."
            )
            return {'success': True, 'message': f'Pesanan #{order_id} berhasil diproses.'}

        except mysql.connector.Error as e:
            conn.rollback()
            logger.error(
                f"Kesalahan database selama pemrosesan pembayaran untuk transaksi {transaction_id}, "
                f"ID Pesanan {order_id}: {e}",
                exc_info=True
            )
            return {
                'success': False,
                'message': 'Kesalahan database saat memproses pembayaran.'
            }

        except Exception as e:
            conn.rollback()
            logger.error(
                f"Kesalahan tak terduga saat memproses webhook pembayaran untuk transaction_id {transaction_id}, "
                f"ID Pesanan {order_id}: {e}",
                exc_info=True
            )
            return {'success': False, 'message': f'Gagal memproses pembayaran: {e}'}

        finally:
            cursor.close()
            conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk process_successful_payment "
                f"(Transaksi {transaction_id})."
            )


payment_service = PaymentService()