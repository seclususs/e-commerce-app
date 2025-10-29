from typing import Any, Dict, List, Optional, Tuple

from mysql.connector.connection import MySQLConnection


class StockRepository:

    def delete_expired(self, conn: MySQLConnection) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM stock_holds WHERE expires_at < CURRENT_TIMESTAMP"
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def get_held_stock_sum(
        self, conn: MySQLConnection,
        product_id: int, variant_id: Optional[int],
    ) -> int:
        cursor = conn.cursor(dictionary=True)
        try:
            if variant_id is None:
                query = (
                    "SELECT SUM(quantity) as held FROM stock_holds "
                    "WHERE product_id = %s AND variant_id IS NULL"
                )
                params = (product_id,)
            else:
                query = (
                    "SELECT SUM(quantity) as held FROM stock_holds "
                    "WHERE product_id = %s AND variant_id = %s"
                )
                params = (product_id, variant_id)

            cursor.execute(query, params)
            held_stock_row = cursor.fetchone()
            return (
                held_stock_row["held"]
                if held_stock_row and held_stock_row["held"]
                else 0
            )
        finally:
            cursor.close()


    def delete_by_user_id(self, conn: MySQLConnection, user_id: int) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM stock_holds WHERE user_id = %s", (user_id,)
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def delete_by_session_id(
        self, conn: MySQLConnection, session_id: str
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM stock_holds WHERE session_id = %s", (session_id,)
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def create_batch(
        self, conn: MySQLConnection, holds_data: List[Tuple]
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.executemany(
                """
                INSERT INTO stock_holds (
                    user_id, session_id, product_id, variant_id, quantity,
                    expires_at
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                holds_data,
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def find_simple_by_user_id(
        self, conn: MySQLConnection, user_id: int
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT product_id, variant_id, quantity
                FROM stock_holds
                WHERE user_id = %s AND expires_at > CURRENT_TIMESTAMP
                """,
                (user_id,),
            )
            return cursor.fetchall()
        finally:
            cursor.close()


    def find_simple_by_session_id(
        self, conn: MySQLConnection, session_id: str
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT product_id, variant_id, quantity
                FROM stock_holds
                WHERE session_id = %s AND expires_at > CURRENT_TIMESTAMP
                """,
                (session_id,),
            )
            return cursor.fetchall()
        finally:
            cursor.close()


    def find_detailed_by_user_id(
        self, conn: MySQLConnection, user_id: int
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT p.id AS product_id, p.name, sh.quantity,
                       sh.variant_id, pv.size
                FROM stock_holds sh
                JOIN products p ON sh.product_id = p.id
                LEFT JOIN product_variants pv ON sh.variant_id = pv.id
                WHERE sh.user_id = %s
                AND sh.expires_at > CURRENT_TIMESTAMP
                """,
                (user_id,),
            )
            return cursor.fetchall()
        finally:
            cursor.close()


    def find_detailed_by_session_id(
        self, conn: MySQLConnection, session_id: str
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT p.id AS product_id, p.name, sh.quantity,
                       sh.variant_id, pv.size
                FROM stock_holds sh
                JOIN products p ON sh.product_id = p.id
                LEFT JOIN product_variants pv ON sh.variant_id = pv.id
                WHERE sh.session_id = %s
                AND sh.expires_at > CURRENT_TIMESTAMP
                """,
                (session_id,),
            )
            return cursor.fetchall()
        finally:
            cursor.close()

stock_repository = StockRepository()