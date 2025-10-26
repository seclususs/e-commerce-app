from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursorDict

from app.core.db import get_db_connection
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class SchedulerService:
    def cancel_expired_pending_orders(self) -> Dict[str, Any]:
        logger.info(
            "Scheduler: Memulai tugas untuk membatalkan pesanan "
            "tertunda yang kedaluwarsa."
        )
        
        conn: Optional[MySQLConnection] = None
        cursor: Optional[MySQLCursorDict] = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            expiration_time: datetime = datetime.now() - timedelta(hours=24)
            logger.debug(
                "Scheduler: Ambang batas kedaluwarsa diatur ke "
                f"{expiration_time}"
            )

            query: str = (
                "SELECT id FROM orders "
                "WHERE status = 'Menunggu Pembayaran' AND order_date < %s"
            )

            cursor.execute(query, (expiration_time,))
            expired_orders: List[Dict[str, Any]] = cursor.fetchall()

            if not expired_orders:
                logger.info(
                    "Scheduler: Tidak ditemukan pesanan tertunda "
                    "yang kedaluwarsa."
                )
                return {"success": True, "cancelled_count": 0}

            cancelled_ids: List[int] = [
                order["id"] for order in expired_orders
            ]
            logger.info(
                f"Scheduler: Ditemukan {len(cancelled_ids)} "
                f"pesanan kedaluwarsa: {cancelled_ids}"
            )

            placeholders: str = ", ".join(["%s"] * len(cancelled_ids))

            update_query: str = (
                "UPDATE orders SET status = 'Dibatalkan' "
                f"WHERE id IN ({placeholders})"
            )

            cursor.execute(update_query, tuple(cancelled_ids))

            conn.commit()
            logger.info(
                "Scheduler: Berhasil membatalkan "
                f"{len(cancelled_ids)} pesanan kedaluwarsa."
            )

            return {"success": True, "cancelled_count": len(cancelled_ids)}

        except mysql.connector.Error as db_err:
            logger.error(
                "Scheduler: Kesalahan database saat membatalkan "
                f"pesanan kedaluwarsa: {db_err}",
                exc_info=True,
            )
            if conn and conn.is_connected():
                conn.rollback()
            raise DatabaseException(
                "Kesalahan database saat membatalkan pesanan "
                f"kedaluwarsa: {db_err}"
            )
        
        except Exception as e:
            logger.error(
                "Scheduler: Kesalahan saat membatalkan pesanan "
                f"kedaluwarsa: {e}",
                exc_info=True,
            )
            if conn and conn.is_connected():
                conn.rollback()
            raise ServiceLogicError(
                "Terjadi kesalahan internal saat membatalkan "
                f"pesanan: {e}"
            )

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug("Scheduler: Koneksi database ditutup.")


scheduler_service = SchedulerService()