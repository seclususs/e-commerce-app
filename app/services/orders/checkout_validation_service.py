from typing import Any, Dict, Optional

import mysql.connector

from app.core.db import get_db_connection
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class CheckoutValidationService:

    def check_pending_order(self, user_id: int) -> Optional[Dict[str, Any]]:
        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT id
                FROM orders
                WHERE user_id = %s
                AND status = 'Menunggu Pembayaran'
                ORDER BY order_date DESC
                LIMIT 1
                """,
                (user_id,),
            )

            pending_order = cursor.fetchone()

            if pending_order:
                logger.debug(
                    f"Pesanan tertunda ditemukan untuk pengguna {user_id}: ID {pending_order['id']}"
                )

            else:
                logger.debug(
                    f"Tidak ada pesanan tertunda yang ditemukan untuk pengguna {user_id}"
                )

            return pending_order
        
        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database memeriksa pesanan tertunda untuk pengguna {user_id}: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat memeriksa pesanan tertunda: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan memeriksa pesanan tertunda untuk pengguna {user_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat memeriksa pesanan tertunda: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()
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
            f"Validasi alamat untuk pengguna {user.get('id', 'N/A')}: {'Valid' if is_valid else 'Tidak Valid'}"
        )

        return is_valid


    def check_guest_email_exists(self, email: str) -> bool:

        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            exists = cursor.fetchone() is not None
            logger.debug(
                f"Pemeriksaan keberadaan email tamu '{email}': {'Ada' if exists else 'Tidak Ada'}"
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
                f"Kesalahan memeriksa email tamu '{email}': {e}", exc_info=True
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat memeriksa email tamu: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

checkout_validation_service = CheckoutValidationService()