from typing import Any, Dict, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection
from werkzeug.security import check_password_hash, generate_password_hash

from app.core.db import get_db_connection
from app.exceptions.api_exceptions import AuthError, ValidationError
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
)
from app.exceptions.service_exceptions import ServiceLogicError
from app.repository.membership_repository import (
    MembershipRepository, membership_repository
)
from app.repository.user_repository import UserRepository, user_repository
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class UserService:

    def __init__(
        self,
        user_repo: UserRepository = user_repository,
        member_repo: MembershipRepository = membership_repository
    ):
        self.user_repository = user_repo
        self.membership_repository = member_repo


    def get_user_by_id(self, user_id: int) -> Dict[str, Any]:
        
        logger.debug(f"Mengambil pengguna berdasarkan ID: {user_id}")
        conn: Optional[MySQLConnection] = None

        try:
            conn = get_db_connection()
            user = self.user_repository.find_by_id(conn, user_id)
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
        
        except RecordNotFoundError as rnfe:
            raise rnfe
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat mengambil pengguna ID {user_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(f"Gagal mengambil data pengguna: {e}")
        
        finally:
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

        try:
            conn = get_db_connection()
            conn.start_transaction()
            existing = self.user_repository.check_existing(
                conn, username, email, user_id
            )
            if existing:
                logger.warning(
                    f"Pembaruan gagal untuk pengguna {user_id}: Nama pengguna "
                    f"'{username}' atau email '{email}' sudah digunakan."
                )
                raise ValidationError(
                    "Username atau email sudah digunakan oleh akun lain."
                )
            self.user_repository.update_profile(
                conn, user_id, username, email
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
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk update_user_info "
                f"(ID: {user_id})."
            )


    def change_user_password(
        self, user_id: int, current_password: str, new_password: str
    ) -> Dict[str, Any]:
        
        logger.debug(f"Mencoba mengubah kata sandi untuk pengguna ID: {user_id}")
        conn: Optional[MySQLConnection] = None

        try:
            conn = get_db_connection()
            conn.start_transaction()
            user = self.user_repository.find_by_id(conn, user_id)
            if not user or not check_password_hash(
                user["password"], current_password
            ):
                logger.warning(
                    f"Perubahan kata sandi gagal untuk pengguna {user_id}: "
                    "Kata sandi saat ini salah."
                )
                raise AuthError("Password saat ini salah.")
            hashed_password: str = generate_password_hash(new_password)
            self.user_repository.update_password(
                conn, user_id, hashed_password
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
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk change_user_password "
                f"(ID: {user_id})."
            )


    def update_user_address(
        self,
        user_id: int,
        address_data: Dict[str, Any],
        conn: Optional[MySQLConnection] = None,
    ) -> Dict[str, Any]:
        
        logger.debug(
            f"Mencoba memperbarui alamat untuk pengguna ID: {user_id}. "
            f"Data: {address_data}"
        )
        is_external_conn: bool = conn is not None
        if not is_external_conn:
            logger.debug("Membuat koneksi DB baru untuk update_user_address.")
            conn = get_db_connection()

        try:
            self.user_repository.update_address(conn, user_id, address_data)
            if not is_external_conn:
                conn.commit()
            logger.info(
                f"Alamat berhasil diperbarui untuk pengguna ID: {user_id}."
            )
            return {"success": True, "message": "Alamat berhasil diperbarui."}
        
        except mysql.connector.Error as db_err:
            if not is_external_conn and conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan database saat memperbarui alamat untuk "
                f"pengguna ID {user_id}: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat memperbarui alamat: {db_err}"
            )
        
        except Exception as e:
            if not is_external_conn and conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan saat memperbarui alamat untuk "
                f"pengguna ID {user_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(f"Gagal memperbarui alamat: {e}")
        
        finally:
            if not is_external_conn and conn and conn.is_connected():
                conn.close()
                logger.debug(
                    f"Koneksi DB ditutup untuk update_user_address "
                    f"(ID: {user_id})."
                )
            elif is_external_conn:
                logger.debug(
                    f"Kursor ditutup untuk update_user_address "
                    f"(ID: {user_id}, koneksi eksternal)."
                )

    def get_active_subscription(
        self, user_id: int, conn: Optional[MySQLConnection] = None
    ) -> Optional[Dict[str, Any]]:
        
        logger.debug(f"Mengecek langganan aktif untuk pengguna ID: {user_id}")
        close_conn: bool = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        
        try:
            subscription = (
                self.membership_repository.find_active_subscription_by_user_id(
                    conn, user_id
                )
            )
            if subscription:
                logger.debug(
                    f"Langganan aktif ditemukan untuk pengguna {user_id}: "
                    f"{subscription.get('name')}"
                )
            else:
                logger.debug(
                    f"Tidak ada langganan aktif ditemukan untuk pengguna {user_id}"
                )
            return subscription
        
        except mysql.connector.Error as db_err:
            logger.error(
                f"Kesalahan database saat mengecek langganan untuk pengguna {user_id}: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat mengecek langganan: {db_err}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat mengecek langganan untuk pengguna {user_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(f"Gagal mengecek status langganan: {e}")
        
        finally:
            if close_conn and conn and conn.is_connected():
                conn.close()

user_service = UserService(user_repository, membership_repository)