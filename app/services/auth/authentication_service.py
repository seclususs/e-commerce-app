from typing import Any, Dict, Optional

import mysql.connector
from werkzeug.security import check_password_hash

from app.core.db import get_db_connection
from app.exceptions.api_exceptions import AuthError
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class AuthenticationService:

    def verify_user_login(
        self, username: str, password: str
    ) -> Dict[str, Any]:
        logger.debug(
            f"Mencoba memverifikasi login untuk nama pengguna: {username}"
        )
        
        conn: Optional[Any] = None
        cursor: Optional[Any] = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))

            user: Optional[Dict[str, Any]] = cursor.fetchone()

            if user and check_password_hash(user["password"], password):
                logger.info(
                    f"Login berhasil untuk pengguna: {username} (ID: {user['id']})"
                )
                return user
            
            else:
                logger.warning(
                    f"Login gagal untuk nama pengguna: {username}. "
                    f"Pengguna ditemukan: {'Ya' if user else 'Tidak'}"
                )
                raise AuthError("Username atau password salah.")

        except mysql.connector.Error as db_err:
            logger.error(
                f"Kesalahan database saat verifikasi login untuk {username}: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database selama verifikasi login: {db_err}"
            )
        
        except AuthError as ae:
            raise ae
        
        except Exception as e:
            logger.error(
                f"Kesalahan tak terduga saat verifikasi login untuk {username}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat verifikasi login: {e}"
            )

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk verify_user_login "
                f"(nama pengguna: {username})."
            )

authentication_service = AuthenticationService()