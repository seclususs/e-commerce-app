from typing import Any, Dict, List, Optional, Tuple

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.core.db import get_db_connection
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
)
from app.exceptions.service_exceptions import ServiceLogicError
from app.repository.order_item_repository import (
    OrderItemRepository, order_item_repository
)
from app.repository.order_repository import OrderRepository, order_repository
from app.utils.logging_utils import get_logger


logger = get_logger(__name__)


class OrderQueryService:

    def __init__(
        self,
        order_repo: OrderRepository = order_repository,
        item_repo: OrderItemRepository = order_item_repository,
    ):
        self.order_repository = order_repo
        self.order_item_repository = item_repo
        

    def get_filtered_admin_orders(
        self,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        
        logger.debug(
            f"Service: Mengambil pesanan admin difilter - Status: {status}, "
            f"Awal: {start_date}, Akhir: {end_date}, Pencarian: {search}"
        )
        conn: Optional[MySQLConnection] = None

        try:
            conn = get_db_connection()
            orders = self.order_repository.find_filtered_admin(
                conn, status, start_date, end_date, search
            )
            logger.info(f"Service: Ditemukan {len(orders)} pesanan.")
            return orders
        
        except mysql.connector.Error as db_err:
            logger.error(
                f"Service: Kesalahan database saat filter pesanan: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat filter pesanan: {db_err}"
            )
        
        except Exception as e:
            logger.error(
                f"Service: Kesalahan tak terduga saat filter pesanan: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Kesalahan tak terduga saat filter pesanan: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                "Service: Koneksi database ditutup untuk "
                "get_filtered_admin_orders"
            )


    def get_order_details_for_admin(
        self, order_id: int
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        
        logger.debug(
            f"Service: Mengambil detail pesanan admin untuk ID: {order_id}"
        )
        conn: Optional[MySQLConnection] = None

        try:
            conn = get_db_connection()
            order = self.order_repository.find_details_for_admin(
                conn, order_id
            )
            if not order:
                raise RecordNotFoundError(
                    f"Pesanan dengan ID {order_id} tidak ditemukan."
                )
            items = self.order_item_repository.find_for_admin_detail(
                conn, order_id
            )
            logger.info(
                f"Service: Mengambil detail pesanan {order_id} dengan "
                f"{len(items)} item."
            )
            return order, items
        
        except mysql.connector.Error as db_err:
            logger.error(
                f"Service: Kesalahan database saat mengambil detail pesanan "
                f"{order_id}: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat mengambil detail pesanan "
                f"{order_id}: {db_err}"
            )
        
        except Exception as e:
            logger.error(
                f"Service: Kesalahan saat mengambil detail pesanan "
                f"{order_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Kesalahan saat mengambil detail pesanan {order_id}: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                "Service: Koneksi database ditutup untuk "
                "get_order_details_for_admin"
            )


    def get_order_details_for_invoice(
        self, order_id: int
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        
        logger.debug(f"Service: Mengambil detail invoice untuk ID: {order_id}")
        conn: Optional[MySQLConnection] = None

        try:
            conn = get_db_connection()
            order = self.order_repository.find_details_for_invoice(
                conn, order_id
            )
            if not order:
                raise RecordNotFoundError(
                    f"Pesanan dengan ID {order_id} tidak ditemukan "
                    "untuk invoice."
                )
            items = self.order_item_repository.find_for_invoice(conn, order_id)
            logger.info(
                f"Service: Mengambil detail invoice {order_id} dengan "
                f"{len(items)} item."
            )
            return order, items
        
        except mysql.connector.Error as db_err:
            logger.error(
                f"Service: Kesalahan database saat mengambil detail invoice "
                f"{order_id}: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Service: Kesalahan database saat mengambil detail invoice "
                f"{order_id}: {db_err}"
            )
        
        except Exception as e:
            logger.error(
                f"Service: Kesalahan saat mengambil detail invoice "
                f"{order_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Service: Kesalahan saat mengambil detail invoice {order_id}: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                "Service: Koneksi database ditutup untuk "
                "get_order_details_for_invoice"
            )

order_query_service = OrderQueryService(
    order_repository, order_item_repository
)