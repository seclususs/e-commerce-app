from typing import Any, Dict, List, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.core.db import get_db_connection
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
    )
from app.exceptions.service_exceptions import ServiceLogicError
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class CategoryService:

    def get_all_categories(self) -> List[Dict[str, Any]]:
        logger.debug("Mengambil semua kategori")

        conn: Optional[MySQLConnection] = None
        cursor: Optional[Any] = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM categories ORDER BY name ASC")
            categories: List[Dict[str, Any]] = cursor.fetchall()
            logger.info(f"Mengambil {len(categories)} kategori")
            return categories
        
        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat mengambil semua kategori: {e}",
                exc_info=True
            )
            raise DatabaseException(
                f"Kesalahan database saat mengambil kategori: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat mengambil semua kategori: {e}", exc_info=True
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat mengambil kategori: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug("Koneksi database ditutup untuk get_all_categories")


    def get_category_by_id(
        self, category_id: int
    ) -> Optional[Dict[str, Any]]:
        logger.debug(f"Mengambil kategori berdasarkan id: {category_id}")
        conn: Optional[MySQLConnection] = None
        cursor: Optional[Any] = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "SELECT * FROM categories WHERE id = %s", (category_id,)
            )

            category: Optional[Dict[str, Any]] = cursor.fetchone()

            if category:
                logger.info(f"Kategori ditemukan untuk id: {category_id}")

            else:
                logger.warning(
                    f"Kategori tidak ditemukan untuk id: {category_id}"
                )
                return None
            
            return category
        
        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat mengambil kategori id {category_id}: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat mengambil kategori: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat mengambil kategori id {category_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat mengambil kategori: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk get_category_by_id {category_id}"
            )


    def create_category(self, name: str) -> Dict[str, Any]:
        logger.debug(f"Mencoba membuat kategori dengan nama: {name}")

        if not name or not name.strip():
            raise ValidationError("Nama kategori tidak boleh kosong.")
        
        conn: Optional[MySQLConnection] = None
        cursor: Optional[Any] = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "INSERT INTO categories (name) VALUES (%s)", (name.strip(),)
            )

            new_id: int = cursor.lastrowid
            conn.commit()

            cursor.execute("SELECT * FROM categories WHERE id = %s", (new_id,))

            new_category: Optional[Dict[str, Any]] = cursor.fetchone()

            logger.info(
                f"Kategori '{name}' berhasil dibuat dengan id: {new_id}"
            )

            return {
                "success": True,
                "message": f'Kategori "{name}" berhasil ditambahkan.',
                "data": new_category,
            }
        
        except mysql.connector.IntegrityError:
            if conn:
                conn.rollback()
            logger.warning(f"Gagal membuat kategori '{name}': Sudah ada.")
            return {
                "success": False,
                "message": f'Kategori "{name}" sudah ada.'
            }
        
        except mysql.connector.Error as e:
            if conn:
                conn.rollback()
            logger.error(
                f"Kesalahan database saat membuat kategori '{name}': {e}",
                exc_info=True
            )
            raise DatabaseException(
                f"Kesalahan database saat membuat kategori: {e}"
            )
        
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(
                f"Kesalahan saat membuat kategori '{name}': {e}", exc_info=True
            )
            raise ServiceLogicError(f'Gagal membuat kategori "{name}".')
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk create_category {name}"
            )


    def update_category(
        self, category_id: int, name: str
    ) -> Dict[str, Any]:
        logger.debug(
            f"Mencoba memperbarui id kategori: {category_id} menjadi nama: {name}"
        )

        if not name or not name.strip():
            raise ValidationError("Nama kategori tidak boleh kosong.")
        
        conn: Optional[MySQLConnection] = None
        cursor: Optional[Any] = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE categories SET name = %s WHERE id = %s",
                (name.strip(), category_id),
            )

            conn.commit()

            if cursor.rowcount > 0:
                logger.info(
                    f"Kategori id {category_id} berhasil diperbarui menjadi '{name}'."
                )
                return {
                    "success": True,
                    "message": "Kategori berhasil diperbarui."
                }
            
            else:
                logger.warning(
                    f"Pembaruan kategori gagal: Kategori id {category_id} tidak ditemukan."
                )
                raise RecordNotFoundError("Kategori tidak ditemukan.")
            
        except mysql.connector.IntegrityError:
            if conn:
                conn.rollback()
            logger.warning(
                f"Gagal memperbarui kategori id {category_id}: Nama '{name}' sudah ada."
            )
            return {
                "success": False,
                "message": f'Nama Kategori "{name}" sudah ada.'
            }
        
        except mysql.connector.Error as e:
            if conn:
                conn.rollback()
            logger.error(
                f"Kesalahan database saat memperbarui kategori id {category_id}: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat memperbarui kategori: {e}"
            )
        
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(
                f"Kesalahan saat memperbarui kategori id {category_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Gagal memperbarui kategori id {category_id}."
            )
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk update_category {category_id}"
            )


    def delete_category(self, category_id: int) -> Dict[str, Any]:
        logger.debug(f"Mencoba menghapus kategori id: {category_id}")

        conn: Optional[MySQLConnection] = None
        cursor: Optional[Any] = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            conn.start_transaction()

            cursor.execute(
                "UPDATE products SET category_id = NULL WHERE category_id = %s",
                (category_id,),
            )

            product_update_count: int = cursor.rowcount

            cursor.execute(
                "DELETE FROM categories WHERE id = %s", (category_id,)
            )

            delete_count: int = cursor.rowcount

            if delete_count > 0:
                conn.commit()
                logger.info(
                    f"Kategori id {category_id} berhasil dihapus. "
                    f"Memperbarui {product_update_count} produk."
                )
                return {
                    "success": True,
                    "message": "Kategori berhasil dihapus."
                }
            
            else:
                conn.rollback()
                logger.warning(
                    f"Penghapusan kategori gagal: Kategori id {category_id} tidak ditemukan."
                )
                raise RecordNotFoundError("Kategori tidak ditemukan.")
            
        except mysql.connector.Error as e:
            if conn:
                conn.rollback()
            logger.error(
                f"Kesalahan database saat menghapus kategori id {category_id}: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat menghapus kategori: {e}"
            )
        
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(
                f"Kesalahan saat menghapus kategori id {category_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError("Gagal menghapus kategori.")
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk delete_category {category_id}"
            )

category_service = CategoryService()