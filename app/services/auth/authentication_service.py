from typing import Any, Dict, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection
from werkzeug.security import check_password_hash

from app.core.db import get_db_connection
from app.exceptions.api_exceptions import AuthError
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.repository.user_repository import UserRepository, user_repository
from app.utils.logging_utils import get_logger


logger = get_logger(__name__)


class AuthenticationService:

    def __init__(self, user_repo: UserRepository = user_repository):
        self.user_repository = user_repo


    def verify_user_login(
        self, username_or_email: str, password: str
    ) -> Dict[str, Any]:
        logger.debug(
            f"Mencoba memverifikasi login untuk: {username_or_email}"
        )

        conn: Optional[MySQLConnection] = None

        try:
            conn = get_db_connection()
            
            user = self.user_repository.find_by_username(conn, username_or_email)
            if not user:
                logger.debug(f"Username '{username_or_email}' tidak ditemukan, mencoba email...")
                user = self.user_repository.find_by_email(conn, username_or_email)

            if user and check_password_hash(user["password"], password):
                logger.info(
                    f"Login berhasil untuk pengguna: {user['username']} (ID: {user['id']})"
                )
                return user
            else:
                logger.warning(
                    f"Login gagal untuk: {username_or_email}. "
                    f"Pengguna ditemukan: {'Ya' if user else 'Tidak'}"
                )
                raise AuthError("Username/Email atau password salah.")

        except mysql.connector.Error as db_err:
            logger.error(
                f"Kesalahan database saat verifikasi login untuk {username_or_email}: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database selama verifikasi login: {db_err}"
            )
        
        except AuthError as ae:
            raise ae
        
        except Exception as e:
            logger.error(
                f"Kesalahan tak terduga saat verifikasi login untuk {username_or_email}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat verifikasi login: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk verify_user_login "
                f"(input: {username_or_email})."
            )

authentication_service = AuthenticationService(user_repository)