from datetime import datetime, timedelta
from app.core.db import get_db_connection
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class SchedulerService:


    def cancel_expired_pending_orders(self):
        logger.info("Scheduler: Memulai tugas untuk membatalkan pesanan tertunda yang kedaluwarsa.")
        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            expiration_time = datetime.now() - timedelta(hours=24)
            logger.debug(f"Scheduler: Ambang batas kedaluwarsa diatur ke {expiration_time}")

            cursor.execute(
                """
                SELECT id FROM orders
                WHERE status = 'Menunggu Pembayaran' AND order_date < %s
                """,
                (expiration_time,)
            )
            expired_orders = cursor.fetchall()

            if not expired_orders:
                logger.info("Scheduler: Tidak ditemukan pesanan tertunda yang kedaluwarsa.")
                return {'success': True, 'cancelled_count': 0}

            cancelled_ids = [order['id'] for order in expired_orders]
            logger.info(f"Scheduler: Ditemukan {len(cancelled_ids)} pesanan kedaluwarsa: {cancelled_ids}")

            placeholders = ', '.join(['%s'] * len(cancelled_ids))
            cursor.execute(
                f"UPDATE orders SET status = 'Dibatalkan' WHERE id IN ({placeholders})",
                tuple(cancelled_ids)
            )

            conn.commit()
            logger.info(f"Scheduler: Berhasil membatalkan {len(cancelled_ids)} pesanan kedaluwarsa.")
            return {'success': True, 'cancelled_count': len(cancelled_ids)}

        except Exception as e:
            logger.error(f"Scheduler: Kesalahan saat membatalkan pesanan kedaluwarsa: {e}", exc_info=True)
            if conn and conn.is_connected():
                conn.rollback()
            return {'success': False, 'message': 'Terjadi kesalahan internal.'}

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug("Scheduler: Koneksi database ditutup.")


scheduler_service = SchedulerService()