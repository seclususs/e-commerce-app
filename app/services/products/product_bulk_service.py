from typing import Any, Dict, List, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.core.db import get_db_connection
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ProductBulkService:

    def handle_bulk_product_action(
        self,
        action: str,
        selected_ids: List[Any],
        category_id: Optional[Any] = None
    ) -> Dict[str, Any]:
        logger.debug(
            f"Menangani aksi massal: {action} untuk ID produk: {selected_ids}, "
            f"ID Kategori: {category_id}"
        )

        if not action or not selected_ids:
            logger.warning(
                "Aksi massal gagal: Tidak ada aksi atau ID produk yang dipilih."
            )
            raise ValidationError("Tidak ada aksi atau produk yang dipilih.")

        conn: Optional[MySQLConnection] = None
        cursor: Optional[Any] = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            placeholders: str = ", ".join(["%s"] * len(selected_ids))
            params: tuple = tuple(selected_ids)
            message: str = ""

            if action == "delete":
                logger.info(
                    f"Menjalankan hapus massal untuk ID produk: {selected_ids}"
                )
                cursor.execute(
                    f"DELETE FROM products WHERE id IN ({placeholders})", params
                )
                message = f"{cursor.rowcount} produk berhasil dihapus."

            elif action == "set_category" and category_id:
                logger.info(
                    f"Menjalankan penetapan kategori massal ke {category_id} untuk ID produk: {selected_ids}"
                )
                params_with_category: tuple = (category_id,) + params
                cursor.execute(
                    f"UPDATE products SET category_id = %s WHERE id IN ({placeholders})",
                    params_with_category,
                )
                message = f"Kategori untuk {cursor.rowcount} produk berhasil diubah."

            else:
                logger.warning(
                    f"Aksi massal gagal: Aksi '{action}' tidak valid atau category_id hilang."
                )
                raise ValidationError("Aksi tidak valid atau data kurang.")
            
            conn.commit()

            logger.info(
                f"Aksi massal '{action}' selesai berhasil. Pesan: {message}"
            )
            
            return {"success": True, "message": message}
        
        except mysql.connector.Error as e:
            if conn:
                conn.rollback()
            logger.error(
                f"Kesalahan database saat aksi massal '{action}' untuk ID {selected_ids}: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat memproses aksi massal: {e}"
            )
        
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(
                f"Kesalahan saat aksi massal '{action}' untuk ID {selected_ids}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                "Terjadi kesalahan saat memproses aksi massal."
            )
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                "Koneksi database ditutup untuk handle_bulk_product_action"
            )

product_bulk_service = ProductBulkService()