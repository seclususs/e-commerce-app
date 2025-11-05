import random
from typing import Any, Dict, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection
from werkzeug.security import generate_password_hash

from app.core.db import get_db_connection
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.repository.user_repository import UserRepository, user_repository
from app.services.orders.voucher_service import (
    VoucherService, voucher_service
)
from app.services.utils.validation_service import (
    ValidationService, validation_service
)
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class RegistrationService:

    def __init__(
        self,
        validation_svc: ValidationService = validation_service,
        user_repo: UserRepository = user_repository,
        voucher_svc: VoucherService = voucher_service,
    ):
        self.validation_service = validation_svc
        self.user_repository = user_repo
        self.voucher_service = voucher_svc


    def register_new_user(
        self, username: str, email: str, password: str
    ) -> Optional[Dict[str, Any]]:
        
        logger.debug(
            f"Mencoba mendaftarkan pengguna baru. "
            f"Nama pengguna: {username}, Email: {email}"
        )
        conn: Optional[MySQLConnection] = None

        try:
            conn = get_db_connection()
            conn.start_transaction()

            is_username_available, _ = (
                self.validation_service.validate_username_availability(
                    username, conn
                )
            )
            if not is_username_available:
                logger.warning(
                    f"Pendaftaran gagal: Nama pengguna '{username}' sudah ada."
                )
                raise ValidationError("Username sudah terdaftar.")
            
            is_email_available, _ = (
                self.validation_service.validate_email_availability(email, conn)
            )
            if not is_email_available:
                logger.warning(f"Pendaftaran gagal: Email '{email}' sudah ada.")
                raise ValidationError("Email sudah terdaftar.")
            
            hashed_password = generate_password_hash(password)
            new_user_id = self.user_repository.create(
                conn, username, email, hashed_password, full_name=username
            )

            self.voucher_service.grant_welcome_voucher(conn, new_user_id)

            conn.commit()

            logger.info(
                f"Pengguna baru berhasil didaftarkan. Nama pengguna: {username}, "
                f"Email: {email}, ID: {new_user_id}"
            )
            new_user = self.user_repository.find_by_id(conn, new_user_id)
            return new_user if new_user else None

        except mysql.connector.Error as db_err:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan database saat registrasi pengguna baru "
                f"untuk {username}: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database selama registrasi: {db_err}"
            )
        
        except ValidationError as ve:
            if conn and conn.is_connected():
                conn.rollback()
            raise ve
        
        except Exception as e:
            logger.error(
                f"Kesalahan tak terduga saat registrasi pengguna baru "
                f"untuk {username}: {e}",
                exc_info=True,
            )
            if conn and conn.is_connected():
                conn.rollback()
            raise ServiceLogicError(f"Kesalahan layanan saat registrasi: {e}")
        
        finally:
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk register_new_user "
                f"(nama pengguna: {username})."
            )


    def register_guest_user(
        self, order_details: Dict[str, Any], password: str
    ) -> Optional[Dict[str, Any]]:
        
        email = order_details.get("email")
        name = order_details.get("name")
        logger.debug(
            f"Mencoba mendaftarkan pengguna tamu. Email: {email}, Nama: {name}"
        )

        conn: Optional[MySQLConnection] = None

        if not email:
            raise ValidationError("Email diperlukan untuk registrasi tamu.")
        if not password:
            raise ValidationError("Password diperlukan untuk registrasi.")

        try:
            conn = get_db_connection()
            conn.start_transaction()

            is_email_available, _ = (
                self.validation_service.validate_email_availability(email, conn)
            )
            if not is_email_available:
                logger.warning(
                    f"Pendaftaran tamu gagal: Email '{email}' sudah ada."
                )
                raise ValidationError("Email sudah terdaftar. Silakan login.")
            
            base_username = email.split('@')[0].lower()
            base_username = ''.join(e for e in base_username if e.isalnum())
            if not base_username:
                 base_username = f"guest_{random.randint(1000, 9999)}"
            
            username = base_username
            attempts = 0

            is_username_available = False
            while attempts < 10:
                is_username_available, _ = (
                    self.validation_service.validate_username_availability(
                        username, conn
                    )
                )
                if is_username_available:
                    break
                username = f"{base_username}{random.randint(10, 999)}"
                attempts += 1
            
            if not is_username_available:
                logger.error(
                    f"Tidak dapat membuat nama pengguna unik untuk tamu "
                    f"berdasarkan '{base_username}'."
                )
                raise ServiceLogicError(
                    "Gagal membuat username unik untuk akun baru."
                )
            
            logger.debug(f"Nama pengguna dibuat untuk tamu: {username}")
            hashed_password = generate_password_hash(password)
            guest_details = {**order_details, "username": username}
            new_user_id = self.user_repository.create_guest(
                conn, guest_details, hashed_password
            )

            self.voucher_service.grant_welcome_voucher(conn, new_user_id)

            conn.commit()

            logger.info(
                f"Pengguna tamu berhasil didaftarkan. "
                f"Nama pengguna: {username}, "
                f"Email: {email}, ID: {new_user_id}"
            )
            new_user = self.user_repository.find_by_id(conn, new_user_id)
            return new_user if new_user else None

        except mysql.connector.Error as db_err:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan database saat registrasi pengguna tamu "
                f"untuk email {email}: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database selama registrasi tamu: {db_err}"
            )
        
        except ValidationError as ve:
            if conn and conn.is_connected():
                conn.rollback()
            raise ve
        
        except Exception as e:
            logger.error(
                f"Kesalahan tak terduga saat registrasi pengguna tamu "
                f"untuk email {email}: {e}",
                exc_info=True,
            )
            if conn and conn.is_connected():
                conn.rollback()
            raise ServiceLogicError(
                f"Kesalahan layanan saat registrasi tamu: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk register_guest_user "
                f"(email: {email})."
            )

registration_service = RegistrationService(
    validation_service, user_repository, voucher_service
)