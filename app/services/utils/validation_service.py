from typing import Any, Optional, Tuple

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.core.db import get_db_connection
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.repository.user_repository import UserRepository, user_repository
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ValidationService:

    def __init__(self, user_repo: UserRepository = user_repository):
        self.user_repository = user_repo


    def validate_username_availability(
        self, username: str, conn: Optional[MySQLConnection] = None
    ) -> Tuple[bool, str]:
        
        logger.debug(
            f"Service: Memvalidasi ketersediaan username: {username}"
        )
        close_conn: bool = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True

        try:
            user = self.user_repository.find_by_username(conn, username)
            is_available: bool = user is None
            message: str = (
                "Username tersedia."
                if is_available
                else "Username sudah digunakan."
            )
            return is_available, message

        except mysql.connector.Error as db_err:
            logger.error(
                "Service: Kesalahan DB saat validasi username "
                f"{username}: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                "Gagal memeriksa ketersediaan username karena "
                "kesalahan database."
            )
        
        except Exception as e:
            logger.error(
                "Service: Kesalahan saat validasi username "
                f"{username}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                "Gagal memeriksa ketersediaan username karena "
                "kesalahan server."
            )
        
        finally:
            if close_conn and conn and conn.is_connected():
                conn.close()


    def validate_email_availability(
        self, email: str, conn: Optional[MySQLConnection] = None
    ) -> Tuple[bool, str]:
        
        logger.debug(f"Service: Memvalidasi ketersediaan email: {email}")
        close_conn: bool = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True

        try:
            user = self.user_repository.find_by_email(conn, email)
            is_available: bool = user is None
            message: str = (
                "Email tersedia."
                if is_available
                else "Email sudah terdaftar."
            )
            return is_available, message
        
        except mysql.connector.Error as db_err:
            logger.error(
                f"Service: Kesalahan DB saat validasi email {email}: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                "Gagal memeriksa ketersediaan email karena "
                "kesalahan database."
            )
        
        except Exception as e:
            logger.error(
                f"Service: Kesalahan saat validasi email {email}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                "Gagal memeriksa ketersediaan email karena "
                "kesalahan server."
            )
        
        finally:
            if close_conn and conn and conn.is_connected():
                conn.close()

validation_service = ValidationService(user_repository)