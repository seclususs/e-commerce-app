from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.core.db import get_db_connection
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.repository.order_repository import (
    OrderRepository, order_repository
)


class SchedulerService:

    def __init__(self, order_repo: OrderRepository = order_repository):
        self.order_repository = order_repo

        
    def cancel_expired_pending_orders(self) -> Dict[str, Any]:

        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            expiration_time: datetime = datetime.now() - timedelta(hours=24)
            expired_orders: List[Dict[str, Any]] = (
                self.order_repository.find_expired_pending_orders(
                    conn, expiration_time
                )
            )
            if not expired_orders:
                return {"success": True, "cancelled_count": 0}

            cancelled_ids: List[int] = [
                order["id"] for order in expired_orders
            ]
            self.order_repository.bulk_update_status(
                conn, cancelled_ids, "Dibatalkan"
            )
            conn.commit()
            return {"success": True, "cancelled_count": len(cancelled_ids)}

        except mysql.connector.Error as db_err:
            if conn and conn.is_connected():
                conn.rollback()
            raise DatabaseException(
                "Kesalahan database saat membatalkan pesanan "
                f"kedaluwarsa: {db_err}"
            )
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            raise ServiceLogicError(
                "Terjadi kesalahan internal saat membatalkan "
                f"pesanan: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()

scheduler_service = SchedulerService(order_repository)