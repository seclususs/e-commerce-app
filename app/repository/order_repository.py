from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from mysql.connector.connection import MySQLConnection


class OrderRepository:
    
    def find_pending_by_user_id(
        self, conn: MySQLConnection, user_id: int
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT id
                FROM orders
                WHERE user_id = %s
                AND status = 'Menunggu Pembayaran'
                ORDER BY order_date DESC
                LIMIT 1
                """,
                (user_id,),
            )
            return cursor.fetchone()
        finally:
            cursor.close()


    def find_by_transaction_id(
        self, conn: MySQLConnection, transaction_id: str
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT id, status, payment_method, user_id
                FROM orders
                WHERE payment_transaction_id = %s
                """,
                (transaction_id,),
            )
            return cursor.fetchone()
        finally:
            cursor.close()


    def update_status(
        self, conn: MySQLConnection, order_id: int, status: str
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE orders SET status = %s WHERE id = %s",
                (status, order_id),
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def update_status_and_notes(
        self, conn: MySQLConnection, order_id: int, status: str, notes: str
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE orders SET status = %s, notes = %s WHERE id = %s",
                (status, notes, order_id),
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def find_by_id_and_user_id_for_update(
        self, conn: MySQLConnection, order_id: int, user_id: int
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM orders WHERE id = %s AND user_id = %s FOR UPDATE",
                (order_id, user_id),
            )
            return cursor.fetchone()
        finally:
            cursor.close()


    def find_by_id_for_update(
        self, conn: MySQLConnection, order_id: int
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT status, tracking_number FROM orders WHERE id = %s FOR UPDATE",
                (order_id,),
            )
            return cursor.fetchone()
        finally:
            cursor.close()


    def find_filtered_admin(
        self, conn: MySQLConnection,
        status: Optional[str],
        start_date: Optional[str],
        end_date: Optional[str],
        search: Optional[str],
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            query = (
                "SELECT o.*, u.username AS customer_name FROM orders o "
                "LEFT JOIN users u ON o.user_id = u.id WHERE 1=1"
            )
            params = []

            if status:
                query += " AND o.status = %s"
                params.append(status)
            if start_date:
                query += " AND DATE(o.order_date) >= %s"
                params.append(start_date)
            if end_date:
                query += " AND DATE(o.order_date) <= %s"
                params.append(end_date)
            if search:
                query += (
                    " AND (CAST(o.id AS CHAR) LIKE %s "
                    "OR u.username LIKE %s "
                    "OR o.shipping_name LIKE %s)"
                )
                search_term = f"%{search}%"
                params.extend([search_term, search_term, search_term])

            query += " ORDER BY o.order_date DESC"
            cursor.execute(query, tuple(params))
            return cursor.fetchall()
        finally:
            cursor.close()


    def find_details_for_admin(
        self, conn: MySQLConnection, order_id: int
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT o.*, u.username AS customer_name, u.email
                FROM orders o
                LEFT JOIN users u ON o.user_id = u.id
                WHERE o.id = %s
                """,
                (order_id,),
            )
            return cursor.fetchone()
        finally:
            cursor.close()


    def find_details_for_invoice(
        self, conn: MySQLConnection, order_id: int
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT o.*, u.email
                FROM orders o
                LEFT JOIN users u ON o.user_id = u.id
                WHERE o.id = %s
                """,
                (order_id,),
            )
            return cursor.fetchone()
        finally:
            cursor.close()


    def update_status_and_tracking(
        self,
        conn: MySQLConnection,
        order_id: int,
        new_status: str,
        tracking_number: Optional[str],
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE orders SET status = %s, tracking_number = %s WHERE id = %s",
                (new_status, tracking_number, order_id),
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def create(
        self, conn: MySQLConnection, user_id: Optional[int],
        subtotal: Decimal, discount_amount: Decimal,
        shipping_cost: Decimal, final_total: Decimal,
        voucher_code: Optional[str], payment_method: str,
        transaction_id: Optional[str], shipping_details: Dict[str, Any],
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO orders (
                    user_id, subtotal, discount_amount, shipping_cost,
                    total_amount, voucher_code, status, payment_method,
                    payment_transaction_id, shipping_name, shipping_phone,
                    shipping_address_line_1, shipping_address_line_2,
                    shipping_city, shipping_province, shipping_postal_code,
                    shipping_email
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s
                )
                """,
                (
                    user_id,
                    subtotal,
                    discount_amount,
                    shipping_cost,
                    final_total,
                    voucher_code.upper() if voucher_code else None,
                    "Pesanan Dibuat",
                    payment_method,
                    transaction_id,
                    shipping_details["name"],
                    shipping_details["phone"],
                    shipping_details["address1"],
                    shipping_details.get("address2", ""),
                    shipping_details["city"],
                    shipping_details["province"],
                    shipping_details["postal_code"],
                    shipping_details["email"],
                ),
            )
            return cursor.lastrowid
        finally:
            cursor.close()


    def find_expired_pending_orders(
        self, conn: MySQLConnection, expiration_time: datetime
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            query = (
                "SELECT id FROM orders "
                "WHERE status = 'Menunggu Pembayaran' AND order_date < %s"
            )
            cursor.execute(query, (expiration_time,))
            return cursor.fetchall()
        finally:
            cursor.close()


    def bulk_update_status(
        self, conn: MySQLConnection, order_ids: List[int], status: str
    ) -> int:
        cursor = conn.cursor()
        try:
            placeholders: str = ", ".join(["%s"] * len(order_ids))
            query: str = f"UPDATE orders SET status = %s WHERE id IN ({placeholders})"
            params = [status] + order_ids
            cursor.execute(query, tuple(params))
            return cursor.rowcount
        finally:
            cursor.close()

order_repository = OrderRepository()