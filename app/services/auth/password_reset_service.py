import uuid
from typing import Any, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.core.db import get_db_connection
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.repository.user_repository import UserRepository, user_repository
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class PasswordResetService:

    def __init__(self, user_repo: UserRepository = user_repository):
        self.user_repository = user_repo


    def handle_password_reset_request(self, email: str) -> None:
        logger.debug(
            f"Menangani permintaan reset kata sandi untuk email: {email}"
        )
        
        conn: Optional[MySQLConnection] = None

        try:
            conn = get_db_connection()
            user = self.user_repository.find_by_email(conn, email)
            if user:
                reset_token = str(uuid.uuid4())
                logger.info(
                    f"Reset kata sandi diminta untuk pengguna "
                    f"'{user['username']}' (ID: {user['id']})."
                )
                logger.info(
                    f"EMAIL SIMULASI: Mengirim email reset ke {email} "
                    f"dengan token: {reset_token}"
                )
            else:
                logger.info(
                    f"Permintaan reset kata sandi untuk email yang tidak ada: {email}"
                )

        except mysql.connector.Error as db_err:
            logger.error(
                f"Kesalahan database saat menangani reset kata sandi "
                f"untuk email {email}: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat menangani reset kata sandi: {db_err}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan tak terduga saat menangani reset kata sandi "
                f"untuk email {email}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat menangani reset kata sandi: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk handle_password_reset_request "
                f"(email: {email})."
            )

password_reset_service = PasswordResetService(user_repository)