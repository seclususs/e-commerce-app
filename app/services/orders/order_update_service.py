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
from app.services.orders.order_cancel_service import (
    OrderCancelService, order_cancel_service
)
from app.utils.logging_utils import get_logger
from app.utils.template_filters import status_class_filter


logger = get_logger(__name__)


class OrderUpdateService:

    def __init__(
        self,
        order_repo: OrderRepository = order_repository,
        history_repo: OrderStatusHistoryRepository = (
            order_status_history_repository
        ),
        cancel_svc: OrderCancelService = order_cancel_service,
    ):
        self.order_repository = order_repo
        self.history_repository = history_repo
        self.order_cancel_service = cancel_svc


    def update_order_status_and_tracking(
        self,
        order_id: int,
        new_status: str,
        tracking_number_input: Optional[str],
    ) -> Dict[str, Any]:
        
        logger.info(
            f"Admin memperbarui pesanan {order_id}: "
            f"Status: {new_status}, Resi: {tracking_number_input}"
        )
        if new_status == "Dibatalkan":
            cancel_result = self.order_cancel_service.cancel_admin_order(
                order_id
            )
            if cancel_result.get("success") and "data" in cancel_result:
                cancel_result["data"]["status_class"] = status_class_filter(
                    cancel_result["data"]["status"]
                )
            return cancel_result

        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            conn.start_transaction()
            order = self.order_repository.find_by_id_for_update(conn, order_id)
            if not order:
                logger.warning(
                    f"Update gagal: Pesanan {order_id} tidak ditemukan."
                )
                raise RecordNotFoundError(
                    f"Pesanan dengan ID {order_id} tidak ditemukan."
                )
            
            original_status = order["status"]
            tracking_number = (
                tracking_number_input.strip()
                if tracking_number_input
                else order["tracking_number"]
            )
            status_changed = original_status != new_status
            tracking_changed = order["tracking_number"] != tracking_number
            if not status_changed and not tracking_changed:
                logger.info(
                    f"Tidak ada perubahan data untuk pesanan {order_id}."
                )
                return {
                    "success": True,
                    "message": "Tidak ada perubahan pada data pesanan.",
                    "data": {
                        "id": order_id,
                        "status": original_status,
                        "status_class": status_class_filter(original_status),
                        "tracking_number": order["tracking_number"],
                    },
                }

            self.order_repository.update_status_and_tracking(
                conn, order_id, new_status, tracking_number
            )
            notes = (
                f'Status diubah dari "{original_status}" menjadi '
                f'"{new_status}".'
            )
            if tracking_changed:
                notes += f" Nomor resi: {tracking_number}"
            self.history_repository.create(conn, order_id, new_status, notes)
            conn.commit()

            logger.info(
                f"Pesanan {order_id} berhasil diperbarui. "
                f"Status: {new_status}, Resi: {tracking_number}"
            )
            return {
                "success": True,
                "message": f"Pesanan #{order_id} berhasil diperbarui",
                "data": {
                    "id": order_id,
                    "status": new_status,
                    "status_class": status_class_filter(new_status),
                    "tracking_number": tracking_number,
                },
            }
        
        except (mysql.connector.Error, DatabaseException) as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan database saat memperbarui pesanan {order_id}: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat memperbarui pesanan: {e}"
            )
        
        except (RecordNotFoundError, InvalidOperationError) as user_error:
            if conn and conn.is_connected():
                conn.rollback()
            logger.warning(
                f"Gagal memperbarui pesanan {order_id}: {user_error}"
            )
            raise user_error
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan saat memperbarui pesanan {order_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(f"Gagal memperbarui status pesanan: {e}")
        
        finally:
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                "Koneksi database ditutup untuk "
                f"update_order_status_and_tracking {order_id}"
            )

order_update_service = OrderUpdateService(
    order_repository, order_status_history_repository, order_cancel_service
)