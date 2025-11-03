from typing import Any, Dict, List, Tuple

from mysql.connector.connection import MySQLConnection


class OrderItemRepository:

    def find_by_order_id(
        self, conn: MySQLConnection, order_id: int
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM order_items WHERE order_id = %s", (order_id,)
            )
            return cursor.fetchall()
        finally:
            cursor.close()


    def find_for_invoice(
        self, conn: MySQLConnection, order_id: int
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT p.name, oi.quantity, oi.price
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = %s
                """,
                (order_id,),
            )
            return cursor.fetchall()
        finally:
            cursor.close()


    def find_for_admin_detail(
        self, conn: MySQLConnection, order_id: int
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT p.name, oi.quantity, oi.price,
                       oi.color_at_order, oi.size_at_order
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = %s
                """,
                (order_id,),
            )
            return cursor.fetchall()
        finally:
            cursor.close()


    def create_batch(
        self, conn: MySQLConnection, items_data: List[Tuple]
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.executemany(
                """
                INSERT INTO order_items (
                    order_id, product_id, variant_id, quantity, price,
                    color_at_order, size_at_order
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                items_data,
            )
            return cursor.rowcount
        finally:
            cursor.close()

order_item_repository = OrderItemRepository()