from typing import Any, Dict, List, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.core.db import get_db_connection
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.repository.product_repository import (
    ProductRepository, product_repository
)
from app.utils.logging_utils import get_logger


logger = get_logger(__name__)


class ProductBulkService:

    def __init__(self, product_repo: ProductRepository = product_repository):
        self.product_repository = product_repo


    def handle_bulk_product_action(
        self,
        action: str,
        selected_ids: List[Any],
        category_id: Optional[Any] = None,
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
        message: str = ""
        rows_affected: int = 0

        try:
            conn = get_db_connection()
            conn.start_transaction()
            
            if action == "delete":
                logger.info(
                    f"Menjalankan hapus massal untuk ID produk: {selected_ids}"
                )
                rows_affected = self.product_repository.delete_batch(
                    conn, selected_ids
                )
                message = f"{rows_affected} produk berhasil dihapus."
            
            elif action == "set_category" and category_id:
                logger.info(
                    f"Menjalankan penetapan kategori massal ke {category_id} untuk ID produk: {selected_ids}"
                )
                rows_affected = self.product_repository.update_category_batch(
                    conn, selected_ids, category_id
                )
                message = (
                    f"Kategori untuk {rows_affected} produk berhasil diubah."
                )
            
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
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                "Koneksi database ditutup untuk handle_bulk_product_action"
            )

product_bulk_service = ProductBulkService(product_repository)