from datetime import datetime, timedelta
from app.core.db import get_db_connection
import mysql.connector
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class StockService:


    def get_available_stock(self, product_id, variant_id=None, conn=None):
        item_id = (
            f"Produk {product_id}"
            + (f", Varian {variant_id}" if variant_id else "")
        )
        logger.debug(f"Mengambil stok tersedia untuk {item_id}")

        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
            logger.debug("Membuat koneksi DB baru untuk get_available_stock.")

        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("DELETE FROM stock_holds WHERE expires_at < CURRENT_TIMESTAMP")
            deleted_count = cursor.rowcount
            if deleted_count > 0:
                conn.commit()
                logger.info(f"Membersihkan {deleted_count} penahanan stok yang kedaluwarsa.")
            else:
                conn.rollback()

            base_stock_query = (
                "SELECT stock FROM product_variants WHERE id = %s"
                if variant_id
                else "SELECT stock FROM products WHERE id = %s"
            )
            stock_id = variant_id if variant_id else product_id

            cursor.execute(base_stock_query, (stock_id,))
            product_stock_row = cursor.fetchone()
            if not product_stock_row:
                logger.warning(f"Pemeriksaan stok gagal: {item_id} tidak ditemukan di database.")
                return 0

            product_stock = product_stock_row["stock"]
            logger.debug(f"Stok dasar untuk {item_id}: {product_stock}")

            held_stock_query = "SELECT SUM(quantity) as held FROM stock_holds WHERE product_id = %s"
            params = [product_id]
            if variant_id:
                held_stock_query += " AND variant_id = %s"
                params.append(variant_id)
            else:
                held_stock_query += " AND variant_id IS NULL"

            cursor.execute(held_stock_query, tuple(params))
            held_stock_row = cursor.fetchone()
            held_stock = held_stock_row["held"] if held_stock_row and held_stock_row["held"] else 0
            logger.debug(f"Stok yang ditahan untuk {item_id}: {held_stock}")

            available = max(0, product_stock - held_stock)
            logger.info(
                f"Stok tersedia yang dihitung untuk {item_id}: {available} "
                f"(Dasar: {product_stock}, Ditahan: {held_stock})"
            )
            return available

        except mysql.connector.Error as e:
            logger.error(f"Kesalahan database saat mengambil stok tersedia untuk {item_id}: {e}", exc_info=True)
            return 0

        finally:
            cursor.close()
            if close_conn:
                conn.close()
                logger.debug("Menutup koneksi DB untuk get_available_stock.")


    def hold_stock_for_checkout(self, user_id, session_id, cart_items):
        log_id = f"User {user_id}" if user_id else f"Session {session_id}"
        logger.info(
            f"Mencoba menahan stok untuk checkout bagi {log_id}. "
            f"Jumlah item: {len(cart_items)}"
        )

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            conn.start_transaction()
            logger.debug(f"Memulai transaksi untuk penahanan stok - {log_id}")

            if user_id:
                cursor.execute("DELETE FROM stock_holds WHERE user_id = %s", (user_id,))
                logger.info(
                    f"Membersihkan penahanan stok yang ada untuk pengguna {user_id}. "
                    f"Baris terpengaruh: {cursor.rowcount}"
                )
            elif session_id:
                cursor.execute("DELETE FROM stock_holds WHERE session_id = %s", (session_id,))
                logger.info(
                    f"Membersihkan penahanan stok yang ada untuk sesi {session_id}. "
                    f"Baris terpengaruh: {cursor.rowcount}"
                )
            else:
                logger.error("Penahanan stok gagal: user_id dan session_id keduanya None.")
                conn.rollback()
                return {"success": False, "message": "User ID atau Session ID diperlukan."}

            failed_item_info = None

            for item in cart_items:
                product_id = item.get("id") or item.get("product_id")
                variant_id = item.get("variant_id")
                item_name = item.get("name", f"ID {product_id}")
                item_log_id = (
                    f"Produk {product_id}"
                    + (f", Varian {variant_id}" if variant_id else "")
                )

                available_stock = self.get_available_stock(product_id, variant_id, conn)
                logger.debug(
                    f"Pemeriksaan stok untuk penahanan: {item_log_id}, Diperlukan: {item['quantity']}, "
                    f"Tersedia: {available_stock}"
                )
                if item["quantity"] > available_stock:
                    size_info = f" (Ukuran: {item.get('size', 'N/A')})" if item.get("size") else ""
                    failed_item_info = f"'{item_name}'{size_info} (tersisa {available_stock})"
                    logger.warning(
                        f"Penahanan stok gagal untuk {log_id}: Stok tidak mencukupi untuk {item_log_id}. "
                        f"Diperlukan: {item['quantity']}, Tersedia: {available_stock}"
                    )
                    conn.rollback()
                    return {
                        "success": False,
                        "message": f"Stok untuk {failed_item_info} tidak mencukupi."
                    }

            expires_at = datetime.now() + timedelta(minutes=10)
            holds_to_insert = [
                (
                    user_id,
                    session_id,
                    item.get("id") or item.get("product_id"),
                    item.get("variant_id"),
                    item["quantity"],
                    expires_at
                )
                for item in cart_items
            ]
            logger.debug(
                f"Mempersiapkan {len(holds_to_insert)} catatan penahanan stok untuk dimasukkan."
            )

            cursor.executemany(
                "INSERT INTO stock_holds (user_id, session_id, product_id, variant_id, quantity, expires_at) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                holds_to_insert
            )
            logger.info(
                f"Memasukkan {cursor.rowcount} catatan penahanan stok untuk {log_id}. "
                f"Kedaluwarsa pada {expires_at.isoformat()}"
            )

            conn.commit()
            logger.info(f"Transaksi penahanan stok berhasil di-commit untuk {log_id}")
            return {"success": True, "expires_at": expires_at.isoformat()}

        except mysql.connector.Error as e:
            logger.error(f"Kesalahan database saat menahan stok untuk {log_id}: {e}", exc_info=True)
            conn.rollback()
            return {"success": False, "message": "Terjadi kesalahan database saat validasi stok."}

        except Exception as e:
            logger.error(f"Kesalahan tak terduga saat menahan stok untuk {log_id}: {e}", exc_info=True)
            conn.rollback()
            return {"success": False, "message": "Terjadi kesalahan saat validasi stok."}

        finally:
            cursor.close()
            conn.close()
            logger.debug("Koneksi database ditutup untuk hold_stock_for_checkout.")


    def release_stock_holds(self, user_id, session_id, conn):
        log_id = f"User {user_id}" if user_id else f"Session {session_id}"
        logger.debug(f"Melepaskan penahanan stok untuk {log_id}")

        cursor = conn.cursor()
        try:
            if user_id:
                cursor.execute("DELETE FROM stock_holds WHERE user_id = %s", (user_id,))
            elif session_id:
                cursor.execute("DELETE FROM stock_holds WHERE session_id = %s", (session_id,))
            else:
                logger.warning("Mencoba melepaskan penahanan stok tanpa user_id atau session_id.")
                return

            logger.info(
                f"Melepaskan penahanan stok untuk {log_id}. Baris terpengaruh: {cursor.rowcount}"
            )

        except Exception as e:
            logger.error(f"Kesalahan saat melepaskan penahanan stok untuk {log_id}: {e}", exc_info=True)
            raise e

        finally:
            cursor.close()


    def get_held_items_simple(self, user_id, session_id):
        log_id = f"User {user_id}" if user_id else f"Session {session_id}"
        logger.debug(f"Mengambil daftar item ditahan sederhana untuk {log_id}")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            query = "SELECT product_id, variant_id, quantity FROM stock_holds WHERE "
            params = []

            if user_id:
                query += "user_id = %s"
                params.append(user_id)
            elif session_id:
                query += "session_id = %s"
                params.append(session_id)
            else:
                logger.warning("get_held_items_simple dipanggil tanpa user_id atau session_id.")
                return []

            query += " AND expires_at > CURRENT_TIMESTAMP"

            cursor.execute(query, tuple(params))
            held_items = cursor.fetchall()
            logger.info(f"Menemukan {len(held_items)} item ditahan sederhana untuk {log_id}")
            return held_items

        except Exception as e:
            logger.error(f"Kesalahan saat mengambil item ditahan sederhana untuk {log_id}: {e}", exc_info=True)
            return []

        finally:
            cursor.close()
            conn.close()
            logger.debug("Koneksi database ditutup untuk get_held_items_simple.")


stock_service = StockService()