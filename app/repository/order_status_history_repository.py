from typing import Optional

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

order_status_history_repository = OrderStatusHistoryRepository()