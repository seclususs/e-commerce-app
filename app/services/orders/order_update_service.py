from typing import Any, Dict, Optional

import mysql.connector

from app.core.db import get_db_connection
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
    )
from app.exceptions.service_exceptions import ServiceLogicError
from app.services.orders.order_cancel_service import order_cancel_service
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class OrderUpdateService:

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
            return order_cancel_service.cancel_admin_order(order_id)
        
        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            conn.start_transaction()

            cursor.execute(
                "SELECT status, tracking_number FROM orders WHERE id = %s FOR UPDATE",
                (order_id,),
            )

            order = cursor.fetchone()

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
                        "status_class": original_status.lower().replace(" ", "-"),
                        "tracking_number": order["tracking_number"],
                    },
                }
            
            cursor.execute(
                "UPDATE orders SET status = %s, tracking_number = %s WHERE id = %s",
                (new_status, tracking_number, order_id),
            )

            notes = f'Status diubah dari "{original_status}" menjadi "{new_status}".'

            if tracking_changed:
                notes += f" Nomor resi: {tracking_number}"

            cursor.execute(
                "INSERT INTO order_status_history (order_id, status, notes) VALUES (%s, %s, %s)",
                (order_id, new_status, notes),
            )

            conn.commit()

            logger.info(
                f"Pesanan {order_id} berhasil diperbarui. Status: {new_status}, Resi: {tracking_number}"
            )
            
            return {
                "success": True,
                "message": f"Pesanan #{order_id} berhasil diperbarui",
                "data": {
                    "id": order_id,
                    "status": new_status,
                    "status_class": new_status.lower().replace(" ", "-"),
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
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan saat memperbarui pesanan {order_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(f"Gagal memperbarui status pesanan: {e}")

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk update_order_status_and_tracking {order_id}"
            )

order_update_service = OrderUpdateService()