from db.db_config import get_db_connection
from datetime import datetime, timedelta


class SchedulerService:

    def cancel_expired_pending_orders(self):
        conn = get_db_connection()
        try:
            with conn:
                expiration_time = datetime.now() - timedelta(hours=24)

                expired_orders = conn.execute(
                    "SELECT id FROM orders WHERE status = 'Menunggu Pembayaran' AND order_date < ?",
                    (expiration_time,)
                ).fetchall()

                if not expired_orders:
                    print("Scheduler: Tidak ada pesanan kedaluwarsa yang ditemukan.")
                    return {'success': True, 'cancelled_count': 0}

                cancelled_ids = [order['id'] for order in expired_orders]

                placeholders = ', '.join(['?'] * len(cancelled_ids))
                conn.execute(f"UPDATE orders SET status = 'Dibatalkan' WHERE id IN ({placeholders})", cancelled_ids)

                print(f"Scheduler: Berhasil membatalkan {len(cancelled_ids)} pesanan kedaluwarsa.")
                return {'success': True, 'cancelled_count': len(cancelled_ids)}

        except Exception as e:
            print(f"ERROR saat menjalankan scheduler pembatalan pesanan: {e}")
            return {'success': False, 'message': 'Terjadi kesalahan internal.'}
        finally:
            conn.close()


scheduler_service = SchedulerService()