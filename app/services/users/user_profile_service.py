from typing import Any, Dict, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.core.db import get_db_connection
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
)
from app.exceptions.service_exceptions import ServiceLogicError
from app.repository.user_repository import user_repository, UserRepository


class UserProfileService:

    def __init__(self, user_repo: UserRepository = user_repository):
        self.user_repository = user_repo


    def get_user_by_id(self, user_id: int) -> Dict[str, Any]:

        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            user = self.user_repository.find_by_id(conn, user_id)
            if user:
                return user
            else:
                raise RecordNotFoundError(
                    f"Pengguna dengan ID {user_id} tidak ditemukan."
                )
            
        except mysql.connector.Error as db_err:
            raise DatabaseException(
                f"Kesalahan database saat mengambil pengguna: {db_err}"
            )
        
        except RecordNotFoundError as e:
            raise e
        
        except Exception as e:
            raise ServiceLogicError(f"Gagal mengambil data pengguna: {e}")
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def update_user_info(
        self, user_id: int, username: str, email: str
    ) -> Dict[str, Any]:
        
        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            conn.start_transaction()
            existing = self.user_repository.check_existing(
                conn, username, email, user_id
            )
            if existing:
                raise ValidationError(
                    "Username atau email sudah digunakan oleh akun lain."
                )
            self.user_repository.update_profile(conn, user_id, username, email)
            conn.commit()
            return {
                "success": True,
                "message": "Informasi akun berhasil diperbarui.",
            }
        
        except mysql.connector.Error as db_err:
            if conn and conn.is_connected():
                conn.rollback()
            raise DatabaseException(
                f"Kesalahan database saat memperbarui info pengguna: {db_err}"
            )
        
        except ValidationError as ve:
            if conn and conn.is_connected():
                conn.rollback()
            raise ve
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            raise ServiceLogicError(f"Gagal memperbarui informasi akun: {e}")
        
        finally:
            if conn and conn.is_connected():
                conn.close()

user_profile_service = UserProfileService(user_repository)