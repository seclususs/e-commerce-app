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
from app.repository.report_repository import (
    ReportRepository, report_repository
)
from app.repository.user_voucher_repository import (
    UserVoucherRepository, user_voucher_repository
)
from app.repository.voucher_repository import (
    VoucherRepository, voucher_repository
)
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class SchedulerService:

    def __init__(
        self,
        order_repo: OrderRepository = order_repository,
        report_repo: ReportRepository = report_repository,
        voucher_repo: VoucherRepository = voucher_repository,
        user_voucher_repo: UserVoucherRepository = user_voucher_repository
    ):
        self.order_repository = order_repo
        self.report_repository = report_repo
        self.voucher_repository = voucher_repo
        self.user_voucher_repository = user_voucher_repo

        
    def cancel_expired_pending_orders(self) -> Dict[str, Any]:

        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            conn.start_transaction()
            expiration_time: datetime = datetime.now() - timedelta(hours=24)
            expired_orders: List[Dict[str, Any]] = (
                self.order_repository.find_expired_pending_orders(
                    conn, expiration_time
                )
            )
            if not expired_orders:
                conn.commit()
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


    def grant_segmented_vouchers(self) -> Dict[str, Any]:
        conn: Optional[MySQLConnection] = None
        granted_count = 0
        
        try:
            conn = get_db_connection()
            conn.start_transaction()
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            top_user_ids = (
                self.report_repository.get_top_spenders_user_ids_by_percentile(
                    conn,
                    0.05,
                    start_date.strftime('%Y-%m-%d %H:%M:%S'),
                    end_date.strftime('%Y-%m-%d %H:%M:%S')
                )
            )
            
            if not top_user_ids:
                logger.info("Scheduler: Tidak ada top spender yang ditemukan.")
                conn.commit()
                return {"success": True, "granted_count": 0}

            voucher = self.voucher_repository.find_by_code(
                conn, "TOP_SPENDER"
            )
            
            if not voucher:
                logger.warning(
                    "Scheduler: Voucher 'TOP_SPENDER' tidak ditemukan."
                )
                conn.commit()
                return {"success": False, "granted_count": 0}
                
            voucher_id = voucher["id"]

            for user_id in top_user_ids:
                try:
                    self.user_voucher_repository.create(
                        conn, user_id, voucher_id
                    )
                    granted_count += 1
                except mysql.connector.IntegrityError:
                    logger.debug(
                        f"User {user_id} sudah memiliki voucher TOP_SPENDER."
                    )
                    pass
            
            conn.commit()
            logger.info(
                f"Scheduler: {granted_count} voucher TOP_SPENDER diberikan."
            )
            return {"success": True, "granted_count": granted_count}

        except mysql.connector.Error as db_err:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(f"Scheduler DB error: {db_err}", exc_info=True)
            raise DatabaseException(
                f"Kesalahan database saat memberikan voucher segmen: {db_err}"
            )
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(f"Scheduler service error: {e}", exc_info=True)
            raise ServiceLogicError(
                f"Kesalahan layanan saat memberikan voucher segmen: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()

scheduler_service = SchedulerService(
    order_repository, report_repository,
    voucher_repository, user_voucher_repository
)