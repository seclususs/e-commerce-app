from typing import Any, Dict, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.core.db import get_db_connection
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
)
from app.exceptions.service_exceptions import (
    InvalidOperationError, ServiceLogicError
)
from app.repository.order_repository import OrderRepository, order_repository
from app.repository.order_status_history_repository import (
    OrderStatusHistoryRepository, order_status_history_repository
)
from app.services.orders.stock_service import StockService, stock_service
from app.utils.logging_utils import get_logger
from app.utils.template_filters import status_class_filter


logger = get_logger(__name__)


class OrderCancelService:

    def __init__(
        self,
        order_repo: OrderRepository = order_repository,
        history_repo: OrderStatusHistoryRepository = (
            order_status_history_repository
        ),
        stock_svc: StockService = stock_service,
    ):
        self.order_repository = order_repo
        self.history_repository = history_repo
        self.stock_service = stock_svc


    def cancel_user_order(
        self, order_id: int, user_id: int
    ) -> Dict[str, Any]:
        
        logger.info(
            f"Pengguna {user_id} mencoba membatalkan pesanan {order_id}"
        )
        conn: Optional[MySQLConnection] = None

        try:
            conn = get_db_connection()
            conn.start_transaction()
            order = self.order_repository.find_by_id_and_user_id_for_update(
                conn, order_id, user_id
            )
            if not order:
                logger.warning(
                    f"Pembatalan gagal: Pesanan {order_id} tidak "
                    f"ditemukan untuk pengguna {user_id}"
                )
                raise RecordNotFoundError(
                    "Pesanan tidak ditemukan atau Anda tidak memiliki akses."
                )

            current_status = order["status"]
            if current_status not in ["Menunggu Pembayaran", "Diproses"]:
                logger.warning(
                    f"Pembatalan gagal untuk pesanan {order_id}: Status "
                    f"saat ini '{current_status}' tidak valid."
                )
                raise InvalidOperationError(
                    f'Pesanan tidak dapat dibatalkan karena statusnya '
                    f'"{current_status}".'
                )

            if current_status == "Diproses":
                logger.info(
                    f"Restocking item untuk pesanan {order_id} yang "
                    "dibatalkan."
                )
                self.stock_service.restock_items_for_order(order_id, conn)

            self.order_repository.update_status(conn, order_id, "Dibatalkan")
            self.history_repository.create(
                conn,
                order_id,
                "Dibatalkan",
                "Pesanan dibatalkan oleh pelanggan.",
            )
            conn.commit()

            logger.info(
                f"Pesanan {order_id} berhasil dibatalkan oleh pengguna "
                f"{user_id}."
            )
            return {
                "success": True,
                "message": f"Pesanan #{order_id} dibatalkan.",
            }
        
        except (RecordNotFoundError, InvalidOperationError) as user_error:
            if conn and conn.is_connected():
                conn.rollback()
            return {"success": False, "message": str(user_error)}
        
        except (mysql.connector.Error, DatabaseException) as db_err:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan database saat membatalkan pesanan {order_id} "
                f"oleh pengguna {user_id}: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat membatalkan pesanan: {db_err}"
            )
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan saat membatalkan pesanan {order_id} oleh "
                f"pengguna {user_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(f"Gagal membatalkan pesanan: {e}")
        
        finally:
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk cancel_user_order {order_id}"
            )


    def cancel_admin_order(self, order_id: int) -> Dict[str, Any]:

        logger.info(f"Admin mencoba membatalkan pesanan {order_id}")
        conn: Optional[MySQLConnection] = None

        try:
            conn = get_db_connection()
            conn.start_transaction()
            order = self.order_repository.find_by_id_for_update(conn, order_id)
            if not order:
                logger.warning(
                    f"Pembatalan admin gagal: Pesanan {order_id} tidak "
                    "ditemukan."
                )
                raise RecordNotFoundError("Pesanan tidak ditemukan.")

            current_status = order["status"]
            if current_status == "Dibatalkan":
                logger.info(f"Pesanan {order_id} sudah dibatalkan sebelumnya.")
                raise InvalidOperationError("Pesanan sudah dibatalkan.")

            if current_status in ["Diproses", "Dikirim"]:
                logger.info(
                    f"Restocking item untuk pesanan {order_id} yang "
                    "dibatalkan oleh admin."
                )
                self.stock_service.restock_items_for_order(order_id, conn)

            self.order_repository.update_status(conn, order_id, "Dibatalkan")
            self.history_repository.create(
                conn,
                order_id,
                "Dibatalkan",
                "Pesanan dibatalkan oleh admin.",
            )
            conn.commit()
            
            logger.info(f"Pesanan {order_id} berhasil dibatalkan oleh admin.")
            return {
                "success": True,
                "message": f"Pesanan #{order_id} berhasil dibatalkan.",
                "data": {
                    "status": "Dibatalkan",
                    "status_class": status_class_filter("Dibatalkan"),
                    "tracking_number": None,
                },
            }
        
        except (RecordNotFoundError, InvalidOperationError) as user_error:
            if conn and conn.is_connected():
                conn.rollback()
            raise user_error
        
        except (mysql.connector.Error, DatabaseException) as db_err:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan database saat admin membatalkan pesanan "
                f"{order_id}: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat membatalkan pesanan: {db_err}"
            )
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan saat admin membatalkan pesanan {order_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(f"Gagal membatalkan pesanan: {e}")
        
        finally:
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                "Koneksi database ditutup untuk cancel_admin_order "
                f"{order_id}"
            )

order_cancel_service = OrderCancelService(
    order_repository, order_status_history_repository, stock_service
)