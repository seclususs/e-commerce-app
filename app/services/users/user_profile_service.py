import logging
from typing import Any, Dict, Optional

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


class UserProfileService:

    def get_user_by_id(self, user_id: int) -> Dict[str, Any]:
        logger.debug(f"Mengambil pengguna berdasarkan ID: {user_id}")
        conn: Optional[MySQLConnection] = None
        cursor: Optional[Any] = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))

            user: Optional[Dict[str, Any]] = cursor.fetchone()

            if user:
                logger.info(f"Pengguna ditemukan untuk ID: {user_id}")

            else:
                logger.warning(f"Pengguna tidak ditemukan untuk ID: {user_id}")
                raise RecordNotFoundError(
                    f"Pengguna dengan ID {user_id} tidak ditemukan."
                )
            
            return user
        
        except mysql.connector.Error as db_err:
            logger.error(
                f"Kesalahan database saat mengambil pengguna ID {user_id}: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat mengambil pengguna: {db_err}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat mengambil pengguna ID {user_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(f"Gagal mengambil data pengguna: {e}")
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk get_user_by_id (ID: {user_id})."
            )

    def update_user_info(
        self, user_id: int, username: str, email: str
    ) -> Dict[str, Any]:
        logger.debug(
            f"Mencoba memperbarui info pengguna untuk ID: {user_id}. "
            f"Nama pengguna baru: {username}, Email baru: {email}"
        )

        conn: Optional[MySQLConnection] = None
        cursor: Optional[Any] = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT id FROM users WHERE (username = %s OR email = %s) "
                "AND id != %s",
                (username, email, user_id),
            )

            existing: Optional[Any] = cursor.fetchone()

            if existing:
                logger.warning(
                    f"Pembaruan gagal untuk pengguna {user_id}: Nama pengguna "
                    f"'{username}' atau email '{email}' sudah digunakan."
                )
                raise ValidationError(
                    "Username atau email sudah digunakan oleh akun lain."
                )
            
            cursor.execute(
                "UPDATE users SET username = %s, email = %s WHERE id = %s",
                (username, email, user_id),
            )

            conn.commit()
            logger.info(f"Info pengguna berhasil diperbarui untuk ID: {user_id}")

            return {
                "success": True,
                "message": "Informasi akun berhasil diperbarui.",
            }
        
        except mysql.connector.Error as db_err:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan database saat memperbarui info pengguna untuk "
                f"ID {user_id}: {db_err}",
                exc_info=True,
            )
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
            logger.error(
                f"Kesalahan saat memperbarui info pengguna untuk "
                f"ID {user_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(f"Gagal memperbarui informasi akun: {e}")
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk update_user_info "
                f"(ID: {user_id})."
            )


user_profile_service = UserProfileService()