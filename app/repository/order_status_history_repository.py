from typing import Any, Dict, List, Optional

from mysql.connector.connection import MySQLConnection


class OrderStatusHistoryRepository:

    def create(
        self, conn: MySQLConnection,
        order_id: int, status: str,
        notes: Optional[str] = None,
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO order_status_history (order_id, status, notes)
                VALUES (%s, %s, %s)
                """,
                (order_id, status, notes),
            )
            return cursor.lastrowid
        finally:
            cursor.close()

    def find_by_order_id(
        self, conn: MySQLConnection, order_id: int
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM order_status_history "
                "WHERE order_id = %s ORDER BY timestamp ASC",
                (order_id,),
            )
            return cursor.fetchall()
        finally:
            cursor.close()

order_status_history_repository = OrderStatusHistoryRepository()