import mysql.connector
from app.core.db import get_db_connection
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class OrderQueryService:


    def get_filtered_admin_orders(self, status=None, start_date=None, end_date=None, search=None):
        logger.debug(
            f"Service: Mengambil pesanan admin difilter - Status: {status}, "
            f"Awal: {start_date}, Akhir: {end_date}, Pencarian: {search}"
        )
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            query = (
                'SELECT o.*, u.username AS customer_name FROM orders o '
                'LEFT JOIN users u ON o.user_id = u.id WHERE 1=1'
            )
            params = []

            if status:
                query += ' AND o.status = %s'
                params.append(status)
            if start_date:
                query += ' AND DATE(o.order_date) >= %s'
                params.append(start_date)
            if end_date:
                query += ' AND DATE(o.order_date) <= %s'
                params.append(end_date)
            if search:
                query += (
                    " AND (CAST(o.id AS CHAR) LIKE %s "
                    "OR u.username LIKE %s "
                    "OR o.shipping_name LIKE %s)"
                )
                search_term = f'%{search}%'
                params.extend([search_term, search_term, search_term])

            query += ' ORDER BY o.order_date DESC'

            cursor.execute(query, tuple(params))
            orders = cursor.fetchall()
            logger.info(f"Service: Ditemukan {len(orders)} pesanan.")
            return orders

        except mysql.connector.Error as db_err:
            logger.error(f"Service: Kesalahan database saat filter pesanan: {db_err}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Service: Kesalahan tak terduga saat filter pesanan: {e}", exc_info=True)
            raise
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug("Service: Koneksi database ditutup untuk get_filtered_admin_orders")


    def get_order_details_for_admin(self, order_id):
        logger.debug(f"Service: Mengambil detail pesanan admin untuk ID: {order_id}")
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                'SELECT o.*, u.username AS customer_name, u.email '
                'FROM orders o LEFT JOIN users u ON o.user_id = u.id '
                'WHERE o.id = %s',
                (order_id,)
            )
            order = cursor.fetchone()

            if not order:
                return None, []

            cursor.execute(
                'SELECT p.name, oi.quantity, oi.price, oi.size_at_order '
                'FROM order_items oi JOIN products p ON oi.product_id = p.id '
                'WHERE oi.order_id = %s',
                (order_id,)
            )
            items = cursor.fetchall()
            logger.info(f"Service: Mengambil detail pesanan {order_id} dengan {len(items)} item.")
            return order, items
        except Exception as e:
            logger.error(f"Service: Kesalahan saat mengambil detail pesanan {order_id}: {e}", exc_info=True)
            raise
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug("Service: Koneksi database ditutup untuk get_order_details_for_admin")


    def get_order_details_for_invoice(self, order_id):
        logger.debug(f"Service: Mengambil detail invoice untuk ID: {order_id}")
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                'SELECT o.*, u.email FROM orders o '
                'LEFT JOIN users u ON o.user_id = u.id WHERE o.id = %s',
                (order_id,)
            )
            order = cursor.fetchone()

            if not order:
                return None, []

            cursor.execute(
                'SELECT p.name, oi.quantity, oi.price '
                'FROM order_items oi JOIN products p ON oi.product_id = p.id '
                'WHERE oi.order_id = %s',
                (order_id,)
            )
            items = cursor.fetchall()
            logger.info(f"Service: Mengambil detail invoice {order_id} dengan {len(items)} item.")
            return order, items
        except Exception as e:
            logger.error(f"Service: Kesalahan saat mengambil detail invoice {order_id}: {e}", exc_info=True)
            raise
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug("Service: Koneksi database ditutup untuk get_order_details_for_invoice")


order_query_service = OrderQueryService()