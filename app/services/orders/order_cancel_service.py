from typing import Any, Dict

import mysql.connector

from app.core.db import get_db_connection
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
    )
from app.exceptions.service_exceptions import (
    InvalidOperationError, ServiceLogicError
    )
from app.services.orders.stock_service import stock_service
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class OrderCancelService:

    def cancel_user_order(self, order_id: int, user_id: int) -> Dict[str, Any]:
        logger.info(
            f"Pengguna {user_id} mencoba membatalkan pesanan {order_id}"
        )

        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            conn.start_transaction()

            cursor.execute(
                "SELECT * FROM orders WHERE id = %s AND user_id = %s FOR UPDATE",
                (order_id, user_id),
            )

            order = cursor.fetchone()

            if not order:
                logger.warning(
                    f"Pembatalan gagal: Pesanan {order_id} tidak ditemukan untuk pengguna {user_id}"
                )
                raise RecordNotFoundError(
                    "Pesanan tidak ditemukan atau Anda tidak memiliki akses."
                )
            
            current_status = order["status"]

            if current_status not in ["Menunggu Pembayaran", "Diproses"]:
                logger.warning(
                    f"Pembatalan gagal untuk pesanan {order_id}: Status saat ini '{current_status}' tidak valid."
                )
                raise InvalidOperationError(
                    f'Pesanan tidak dapat dibatalkan karena statusnya "{current_status}".'
                )
            
            if current_status == "Diproses":
                logger.info(
                    f"Restocking item untuk pesanan {order_id} yang dibatalkan."
                )
                stock_service.restock_items_for_order(order_id, conn)

            cursor.execute(
                "UPDATE orders SET status = %s WHERE id = %s",
                ("Dibatalkan", order_id),
            )
            cursor.execute(
                "INSERT INTO order_status_history (order_id, status, notes) VALUES (%s, %s, %s)",
                (order_id, "Dibatalkan", "Pesanan dibatalkan oleh pelanggan."),
            )

            conn.commit()
            logger.info(
                f"Pesanan {order_id} berhasil dibatalkan oleh pengguna {user_id}."
            )

            return {"success": True, "message": f"Pesanan #{order_id} dibatalkan."}
        
        except (RecordNotFoundError, InvalidOperationError) as user_error:
            if conn and conn.is_connected():
                conn.rollback()
            return {"success": False, "message": str(user_error)}
        
        except (mysql.connector.Error, DatabaseException) as db_err:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan database saat membatalkan pesanan {order_id} oleh pengguna {user_id}: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat membatalkan pesanan: {db_err}"
            )
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan saat membatalkan pesanan {order_id} oleh pengguna {user_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(f"Gagal membatalkan pesanan: {e}")
        
        finally:
            if cursor:
                cursor.close()

            if conn and conn.is_connected():
                conn.close()

            logger.debug(
                f"Koneksi database ditutup untuk cancel_user_order {order_id}"
            )


    def cancel_admin_order(self, order_id: int) -> Dict[str, Any]:
        logger.info(f"Admin mencoba membatalkan pesanan {order_id}")
        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            conn.start_transaction()

            cursor.execute(
                "SELECT status FROM orders WHERE id = %s FOR UPDATE", (order_id,)
            )

            order = cursor.fetchone()

            if not order:
                logger.warning(
                    f"Pembatalan admin gagal: Pesanan {order_id} tidak ditemukan."
                )
                raise RecordNotFoundError("Pesanan tidak ditemukan.")
            
            current_status = order["status"]

            if current_status == "Dibatalkan":
                logger.info(f"Pesanan {order_id} sudah dibatalkan sebelumnya.")
                raise InvalidOperationError("Pesanan sudah dibatalkan.")
            
            if current_status in ["Diproses", "Dikirim"]:
                logger.info(
                    f"Restocking item untuk pesanan {order_id} yang dibatalkan oleh admin."
                )
                stock_service.restock_items_for_order(order_id, conn)

            cursor.execute(
                "UPDATE orders SET status = 'Dibatalkan' WHERE id = %s",
                (order_id,),
            )
            cursor.execute(
                "INSERT INTO order_status_history (order_id, status, notes) VALUES (%s, %s, %s)",
                (order_id, "Dibatalkan", "Pesanan dibatalkan oleh admin."),
            )
            
            conn.commit()

            logger.info(f"Pesanan {order_id} berhasil dibatalkan oleh admin.")

            return {
                "success": True,
                "message": f"Pesanan #{order_id} berhasil dibatalkan.",
                "data": {
                    "status": "Dibatalkan",
                    "status_class": "cancelled",
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
                f"Kesalahan database saat admin membatalkan pesanan {order_id}: {db_err}",
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
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk cancel_admin_order {order_id}"
            )

order_cancel_service = OrderCancelService()