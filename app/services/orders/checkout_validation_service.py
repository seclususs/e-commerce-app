from typing import Any, Dict, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.core.db import get_db_connection
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.repository.order_repository import OrderRepository, order_repository
from app.repository.user_repository import UserRepository, user_repository
from app.utils.logging_utils import get_logger


logger = get_logger(__name__)


class CheckoutValidationService:

    def __init__(
        self,
        order_repo: OrderRepository = order_repository,
        user_repo: UserRepository = user_repository,
    ):
        self.order_repository = order_repo
        self.user_repository = user_repo


    def check_pending_order(
        self, user_id: int
    ) -> Optional[Dict[str, Any]]:
        
        conn: Optional[MySQLConnection] = None

        try:
            conn = get_db_connection()
            pending_order = self.order_repository.find_pending_by_user_id(
                conn, user_id
            )
            if pending_order:
                logger.debug(
                    f"Pesanan tertunda ditemukan untuk pengguna {user_id}: "
                    f"ID {pending_order['id']}"
                )
            else:
                logger.debug(
                    f"Tidak ada pesanan tertunda yang ditemukan untuk "
                    f"pengguna {user_id}"
                )
            return pending_order
        
        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database memeriksa pesanan tertunda untuk "
                f"pengguna {user_id}: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat memeriksa pesanan tertunda: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan memeriksa pesanan tertunda untuk "
                f"pengguna {user_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat memeriksa pesanan tertunda: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def validate_user_address(self, user: Optional[Dict[str, Any]]) -> bool:

        if not user:
            return False

        is_valid = all(
            [
                user.get("phone"),
                user.get("address_line_1"),
                user.get("city"),
                user.get("province"),
                user.get("postal_code"),
            ]
        )
        logger.debug(
            f"Validasi alamat untuk pengguna {user.get('id', 'N/A')}: "
            f"{'Valid' if is_valid else 'Tidak Valid'}"
        )
        return is_valid
    

    def check_guest_email_exists(self, email: str) -> bool:

        conn: Optional[MySQLConnection] = None

        try:
            conn = get_db_connection()
            user = self.user_repository.find_by_email(conn, email)
            exists = user is not None
            logger.debug(
                f"Pemeriksaan keberadaan email tamu '{email}': "
                f"{'Ada' if exists else 'Tidak Ada'}"
            )
            return exists
        
        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database memeriksa email tamu '{email}': {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat memeriksa email tamu: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan memeriksa email tamu '{email}': {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat memeriksa email tamu: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()

checkout_validation_service = CheckoutValidationService(
    order_repository, user_repository
)