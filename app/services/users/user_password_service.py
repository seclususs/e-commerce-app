import logging
from typing import Any, Dict, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection
from werkzeug.security import check_password_hash, generate_password_hash

from app.core.db import get_db_connection
from app.exceptions.api_exceptions import AuthError
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class UserPasswordService:

    def change_user_password(
        self, user_id: int, current_password: str, new_password: str
    ) -> Dict[str, Any]:
        logger.debug(f"Mencoba mengubah kata sandi untuk pengguna ID: {user_id}")
        conn: Optional[MySQLConnection] = None
        cursor: Optional[Any] = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT password FROM users WHERE id = %s", (user_id,))

            user: Optional[Dict[str, Any]] = cursor.fetchone()

            if not user or not check_password_hash(
                user["password"], current_password
            ):
                logger.warning(
                    f"Perubahan kata sandi gagal untuk pengguna {user_id}: "
                    "Kata sandi saat ini salah."
                )
                raise AuthError("Password saat ini salah.")

            hashed_password: str = generate_password_hash(new_password)

            cursor.execute(
                "UPDATE users SET password = %s WHERE id = %s",
                (hashed_password, user_id),
            )

            conn.commit()

            logger.info(f"Kata sandi berhasil diubah untuk pengguna ID: {user_id}")
            return {"success": True, "message": "Password berhasil diubah."}
        
        except mysql.connector.Error as db_err:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan database saat mengubah kata sandi untuk "
                f"pengguna ID {user_id}: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat mengubah kata sandi: {db_err}"
            )
        
        except AuthError as ae:
            if conn and conn.is_connected():
                conn.rollback()
            raise ae
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan saat mengubah kata sandi untuk "
                f"pengguna ID {user_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(f"Gagal mengubah password: {e}")

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk change_user_password "
                f"(ID: {user_id})."
            )

user_password_service = UserPasswordService()