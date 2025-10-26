from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import mysql.connector

from app.core.db import get_db_connection
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import (
    OutOfStockError, ServiceLogicError
)
from app.services.products.variant_service import variant_service
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class StockService:

    def get_available_stock(
        self,
        product_id: int,
        variant_id: Optional[int] = None,
        conn: Optional[Any] = None,
    ) -> int:
        stock_check_variant_id: Optional[int] = variant_id
        item_id_log: str = f"Produk {product_id}" + (
            f", Varian {stock_check_variant_id}"
            if stock_check_variant_id is not None else ""
        )
        logger.debug(f"Mengambil stok tersedia untuk {item_id_log}")

        close_conn: bool = False
        cursor: Optional[Any] = None

        if conn is None:
            conn = get_db_connection()
            close_conn = True
            logger.debug(
                "Membuat koneksi DB baru untuk get_available_stock."
            )

        try:
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "DELETE FROM stock_holds WHERE expires_at < CURRENT_TIMESTAMP"
            )
            
            deleted_count: int = cursor.rowcount

            if deleted_count > 0:
                if close_conn or not conn.in_transaction:
                    conn.commit()
                logger.info(
                    f"Membersihkan {deleted_count} penahanan stok "
                    f"yang kedaluwarsa."
                )

            else:
                if close_conn or not conn.in_transaction:
                    conn.rollback()

            base_stock_query: str = (
                "SELECT stock FROM product_variants WHERE id = %s"
                if stock_check_variant_id is not None
                else "SELECT stock FROM products WHERE id = %s"
            )
            stock_id: int = (
                stock_check_variant_id
                if stock_check_variant_id is not None
                else product_id
            )

            cursor.execute(base_stock_query, (stock_id,))
            product_stock_row: Optional[Dict[str, Any]] = cursor.fetchone()

            if not product_stock_row:
                logger.warning(
                    f"Pemeriksaan stok gagal: {item_id_log} tidak "
                    f"ditemukan di database."
                )
                return 0

            product_stock: int = product_stock_row["stock"]
            logger.debug(f"Stok dasar untuk {item_id_log}: {product_stock}")

            if stock_check_variant_id is None:
                held_stock_query: str = (
                    "SELECT SUM(quantity) as held FROM stock_holds "
                    "WHERE product_id = %s AND variant_id IS NULL"
                )
                params: List[int] = [product_id]

            else:
                held_stock_query: str = (
                    "SELECT SUM(quantity) as held FROM stock_holds "
                    "WHERE product_id = %s AND variant_id = %s"
                )
                params = [product_id, stock_check_variant_id]

            cursor.execute(held_stock_query, tuple(params))
            held_stock_row: Optional[Dict[str, Any]] = cursor.fetchone()

            held_stock: int = (
                held_stock_row["held"]
                if held_stock_row and held_stock_row["held"]
                else 0
            )
            logger.debug(f"Stok yang ditahan untuk {item_id_log}: {held_stock}")

            available: int = max(0, product_stock - held_stock)
            logger.info(
                f"Stok tersedia yang dihitung untuk {item_id_log}: {available} "
                f"(Dasar: {product_stock}, Ditahan: {held_stock})"
            )
            return available

        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat mengambil stok tersedia untuk "
                f"{item_id_log}: {e}", exc_info=True
            )
            raise DatabaseException(
                f"Kesalahan database saat mengambil stok: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()
            if close_conn and conn and conn.is_connected():
                conn.close()
                logger.debug("Menutup koneksi DB untuk get_available_stock.")


    def hold_stock_for_checkout(
        self,
        user_id: Optional[int],
        session_id: Optional[str],
        cart_items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        log_id: str = (
            f"User {user_id}" if user_id else f"Session {session_id}"
        )
        logger.info(
            f"Mencoba menahan stok untuk checkout bagi {log_id}. "
            f"Jumlah item: {len(cart_items)}"
        )

        conn: Optional[Any] = None
        cursor: Optional[Any] = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            conn.start_transaction()
            logger.debug(f"Memulai transaksi untuk penahanan stok - {log_id}")

            if user_id:
                cursor.execute(
                    "DELETE FROM stock_holds WHERE user_id = %s", (user_id,)
                )

            elif session_id:
                cursor.execute(
                    "DELETE FROM stock_holds WHERE session_id = %s",
                    (session_id,)
                )

            else:
                raise ValidationError("User ID atau Session ID diperlukan.")
            logger.info(
                f"Membersihkan penahanan stok yang ada untuk {log_id}. "
                f"Baris terpengaruh: {cursor.rowcount}"
            )

            failed_item_info: Optional[str] = None
            holds_to_insert: List[tuple] = []
            expires_at: datetime = datetime.now() + timedelta(minutes=10)

            for item in cart_items:
                product_id: Optional[int] = (
                    item.get("id") or item.get("product_id")
                )
                variant_id: Optional[int] = item.get("variant_id")
                quantity: Optional[int] = item.get("quantity")
                item_name: str = item.get("name", f"ID {product_id}")

                if quantity is None:
                    continue

                item_log_id: str = f"Produk {product_id}" + (
                    f", Varian {variant_id}" if variant_id is not None else ""
                )

                available_stock: int = self.get_available_stock(
                    product_id, variant_id, conn
                )
                logger.debug(
                    f"Pemeriksaan stok untuk penahanan: {item_log_id}, "
                    f"Diperlukan: {quantity}, Tersedia: {available_stock}"
                )

                if quantity > available_stock:
                    size_info: str = (
                        f" (Ukuran: {item.get('size', 'N/A')})"
                        if item.get("size") else ""
                    )
                    failed_item_info = (
                        f"'{item_name}'{size_info} (tersisa {available_stock})"
                    )
                    logger.warning(
                        f"Penahanan stok gagal untuk {log_id}: Stok tidak "
                        f"mencukupi untuk {item_log_id}. "
                        f"Diperlukan: {quantity}, Tersedia: {available_stock}"
                    )
                    raise OutOfStockError(
                        f"Stok untuk {failed_item_info} tidak mencukupi."
                    )

                holds_to_insert.append(
                    (
                        user_id, session_id, product_id, variant_id,
                        quantity, expires_at
                    )
                )

            logger.debug(
                f"Mempersiapkan {len(holds_to_insert)} catatan "
                f"penahanan stok untuk dimasukkan."
            )

            cursor.executemany(
                "INSERT INTO stock_holds (user_id, session_id, product_id, "
                "variant_id, quantity, expires_at) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                holds_to_insert,
            )

            logger.info(
                f"Memasukkan {cursor.rowcount} catatan penahanan stok "
                f"untuk {log_id}. "
                f"Kedaluwarsa pada {expires_at.isoformat()}"
            )

            conn.commit()
            logger.info(
                f"Transaksi penahanan stok berhasil di-commit untuk {log_id}"
            )

            return {"success": True, "expires_at": expires_at.isoformat()}

        except OutOfStockError as oose:
            if conn and conn.is_connected():
                conn.rollback()
            return {"success": False, "message": str(oose)}
        
        except ValidationError as ve:
            if conn and conn.is_connected():
                conn.rollback()
            return {"success": False, "message": str(ve)}
        
        except mysql.connector.Error as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan database saat menahan stok untuk {log_id}: {e}",
                exc_info=True
            )
            raise DatabaseException(
                f"Terjadi kesalahan database saat validasi stok: {e}"
            )
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan tak terduga saat menahan stok untuk {log_id}: {e}",
                exc_info=True
            )
            raise ServiceLogicError(
                f"Terjadi kesalahan saat validasi stok: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                "Koneksi database ditutup untuk hold_stock_for_checkout."
            )


    def release_stock_holds(
        self, user_id: Optional[int], session_id: Optional[str], conn: Any
    ) -> None:
        log_id: str = (
            f"User {user_id}" if user_id else f"Session {session_id}"
        )
        logger.debug(f"Melepaskan penahanan stok untuk {log_id}")

        cursor: Any = conn.cursor()

        try:
            if user_id:
                cursor.execute(
                    "DELETE FROM stock_holds WHERE user_id = %s", (user_id,)
                )

            elif session_id:
                cursor.execute(
                    "DELETE FROM stock_holds WHERE session_id = %s",
                    (session_id,)
                )

            else:
                logger.warning(
                    "Mencoba melepaskan penahanan stok tanpa "
                    "user_id atau session_id."
                )
                return
            logger.info(
                f"Melepaskan penahanan stok untuk {log_id}. "
                f"Baris terpengaruh: {cursor.rowcount}"
            )

        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat melepaskan penahanan stok "
                f"untuk {log_id}: {e}", exc_info=True
            )
            raise DatabaseException(
                f"Kesalahan database saat melepaskan penahanan stok: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat melepaskan penahanan stok untuk {log_id}: {e}",
                exc_info=True
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat melepaskan penahanan stok: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()


    def get_held_items_simple(
        self, user_id: Optional[int], session_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        log_id: str = (
            f"User {user_id}" if user_id else f"Session {session_id}"
        )
        logger.debug(f"Mengambil daftar item ditahan sederhana untuk {log_id}")

        conn: Optional[Any] = None
        cursor: Optional[Any] = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            query: str = (
                "SELECT product_id, variant_id, quantity FROM stock_holds WHERE "
            )

            params: List[int] = []

            if user_id:
                query += "user_id = %s"
                params.append(user_id)

            elif session_id:
                query += "session_id = %s"
                params.append(session_id)

            else:
                return []

            query += " AND expires_at > CURRENT_TIMESTAMP"
            cursor.execute(query, tuple(params))
            held_items: List[Dict[str, Any]] = cursor.fetchall()
            logger.info(
                f"Menemukan {len(held_items)} item ditahan sederhana "
                f"untuk {log_id}"
            )
            return held_items
        
        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat mengambil item ditahan sederhana "
                f"untuk {log_id}: {e}", exc_info=True
            )
            raise DatabaseException(
                f"Kesalahan database saat mengambil item yang ditahan: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat mengambil item ditahan sederhana "
                f"untuk {log_id}: {e}", exc_info=True
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat mengambil item yang ditahan: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                "Koneksi database ditutup untuk get_held_items_simple."
            )

    def restock_items_for_order(
        self, order_id: int, conn: Optional[Any]
    ) -> None:
        is_external_conn: bool = conn is not None
        logger.debug(f"Memulai restock item untuk pesanan {order_id}.")

        cursor: Optional[Any] = None

        if not is_external_conn:
            logger.debug(
                f"Membuat koneksi DB baru untuk "
                f"restock_items_for_order {order_id}."
            )
            conn = get_db_connection()

        else:
            logger.debug(
                f"Menggunakan koneksi DB eksternal untuk "
                f"restock_items_for_order {order_id}."
            )

        try:
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "SELECT * FROM order_items WHERE order_id = %s", (order_id,)
            )

            order_items: List[Dict[str, Any]] = cursor.fetchall()

            if not order_items:
                logger.warning(
                    f"Tidak ada item yang ditemukan untuk restock "
                    f"pada pesanan {order_id}"
                )
                return

            product_ids_with_variants: set[int] = set()

            for item in order_items:
                stock_update_variant_id: Optional[int] = item["variant_id"]

                if stock_update_variant_id is not None:
                    update_query: str = (
                        "UPDATE product_variants SET stock = stock + %s "
                        "WHERE id = %s"
                    )
                    params: tuple = (item["quantity"], stock_update_variant_id)
                    product_ids_with_variants.add(item["product_id"])

                else:
                    update_query: str = (
                        "UPDATE products SET stock = stock + %s WHERE id = %s"
                    )
                    params = (item["quantity"], item["product_id"])

                cursor.execute(update_query, params)

                if cursor.rowcount == 0:
                    logger.warning(
                        f"Gagal melakukan restock untuk item: produk "
                        f"{item['product_id']}, varian "
                        f"{stock_update_variant_id} (mungkin ID tidak valid)"
                    )

            logger.info(
                f"Selesai restock untuk pesanan {order_id}. "
                f"{len(order_items)} jenis item diproses."
            )

            if product_ids_with_variants:
                logger.debug(
                    f"Memperbarui total stok produk untuk "
                    f"{product_ids_with_variants}"
                )

                for product_id in product_ids_with_variants:
                    variant_service.update_total_stock_from_variants(
                        product_id, conn
                    )
                logger.info("Total stok produk dari varian diperbarui.")

        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat restock item untuk pesanan "
                f"{order_id}: {e}", exc_info=True
            )
            raise DatabaseException(f"Kesalahan database saat restock: {e}")
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat restock item untuk pesanan {order_id}: {e}",
                exc_info=True
            )
            raise ServiceLogicError(f"Kesalahan layanan saat restock: {e}")
        
        finally:
            if cursor:
                cursor.close()

            if not is_external_conn and conn and conn.is_connected():
                conn.close()
                logger.debug(
                    f"Koneksi DB ditutup untuk "
                    f"restock_items_for_order {order_id}."
                )

            elif is_external_conn:
                logger.debug(
                    f"Kursor ditutup, koneksi eksternal dijaga tetap "
                    f"terbuka untuk restock_items_for_order {order_id}."
                )

stock_service = StockService()