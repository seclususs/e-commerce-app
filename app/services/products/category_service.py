from typing import Any, Dict, List, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.core.db import get_db_connection
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
)
from app.exceptions.service_exceptions import ServiceLogicError
from app.repository.category_repository import (
    CategoryRepository, category_repository
)


class CategoryService:

    def __init__(self, category_repo: CategoryRepository = category_repository):
        self.category_repository = category_repo


    def get_all_categories(self) -> List[Dict[str, Any]]:
        
        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            return self.category_repository.find_all(conn)
        
        except mysql.connector.Error as e:
            raise DatabaseException(
                f"Kesalahan database saat mengambil kategori: {e}"
            )
        
        except Exception as e:
            raise ServiceLogicError(
                f"Kesalahan layanan saat mengambil kategori: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def get_category_by_id(
        self, category_id: int
    ) -> Optional[Dict[str, Any]]:
        
        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            return self.category_repository.find_by_id(conn, category_id)
        
        except mysql.connector.Error as e:
            raise DatabaseException(
                f"Kesalahan database saat mengambil kategori: {e}"
            )
        
        except Exception as e:
            raise ServiceLogicError(
                f"Kesalahan layanan saat mengambil kategori: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def create_category(self, name: str) -> Dict[str, Any]:

        if not name or not name.strip():
            raise ValidationError("Nama kategori tidak boleh kosong.")

        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            conn.start_transaction()
            new_id = self.category_repository.create(conn, name)
            conn.commit()
            new_category = self.category_repository.find_by_id(conn, new_id)
            return {
                "success": True,
                "message": f'Kategori "{name}" berhasil ditambahkan.',
                "data": new_category,
            }
        
        except mysql.connector.IntegrityError:
            if conn:
                conn.rollback()
            return {
                "success": False,
                "message": f'Kategori "{name}" sudah ada.'
            }
        
        except mysql.connector.Error as e:
            if conn:
                conn.rollback()
            raise DatabaseException(
                f"Kesalahan database saat membuat kategori: {e}"
            )
        
        except Exception as e:
            if conn:
                conn.rollback()
            raise ServiceLogicError(f'Gagal membuat kategori "{name}".')
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def update_category(
        self, category_id: int, name: str
    ) -> Dict[str, Any]:
        
        if not name or not name.strip():
            raise ValidationError("Nama kategori tidak boleh kosong.")

        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            conn.start_transaction()
            rowcount = self.category_repository.update(conn, category_id, name)
            conn.commit()
            if rowcount > 0:
                return {
                    "success": True,
                    "message": "Kategori berhasil diperbarui."
                }
            else:
                raise RecordNotFoundError("Kategori tidak ditemukan.")
            
        except mysql.connector.IntegrityError:
            if conn:
                conn.rollback()
            return {
                "success": False,
                "message": f'Nama Kategori "{name}" sudah ada.'
            }
        
        except mysql.connector.Error as e:
            if conn:
                conn.rollback()
            raise DatabaseException(
                f"Kesalahan database saat memperbarui kategori: {e}"
            )
        
        except Exception as e:
            if conn:
                conn.rollback()
            raise ServiceLogicError(
                f"Gagal memperbarui kategori id {category_id}."
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def delete_category(self, category_id: int) -> Dict[str, Any]:

        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            conn.start_transaction()
            self.category_repository.unlink_products(conn, category_id)
            delete_count = self.category_repository.delete(conn, category_id)
            if delete_count > 0:
                conn.commit()
                return {
                    "success": True,
                    "message": "Kategori berhasil dihapus."
                }
            else:
                conn.rollback()
                raise RecordNotFoundError("Kategori tidak ditemukan.")
            
        except mysql.connector.Error as e:
            if conn:
                conn.rollback()
            raise DatabaseException(
                f"Kesalahan database saat menghapus kategori: {e}"
            )
        
        except Exception as e:
            if conn:
                conn.rollback()
            raise ServiceLogicError("Gagal menghapus kategori.")
        
        finally:
            if conn and conn.is_connected():
                conn.close()

category_service = CategoryService(category_repository)