from typing import Any, Dict, List, Optional

from mysql.connector.connection import MySQLConnection


class ReviewRepository:
    
    def find_by_product_id_with_user(
        self, conn: MySQLConnection, product_id: Any
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT r.*, u.username
                FROM reviews r
                JOIN users u ON r.user_id = u.id
                WHERE r.product_id = %s
                ORDER BY r.created_at DESC
                """,
                (product_id,),
            )
            return cursor.fetchall()
        finally:
            cursor.close()


    def find_by_id_with_user(
        self, conn: MySQLConnection, review_id: Any
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT r.*, u.username
                FROM reviews r
                JOIN users u ON r.user_id = u.id
                WHERE r.id = %s
                """,
                (review_id,),
            )
            return cursor.fetchone()
        finally:
            cursor.close()


    def check_user_purchase(
        self, conn: MySQLConnection, user_id: Any, product_id: Any
    ) -> bool:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT 1
                FROM orders o
                JOIN order_items oi ON o.id = oi.order_id
                WHERE o.user_id = %s
                  AND oi.product_id = %s
                  AND o.status = 'Selesai'
                LIMIT 1
                """,
                (user_id, product_id),
            )
            return cursor.fetchone() is not None
        finally:
            cursor.close()


    def check_user_review_exists(
        self, conn: MySQLConnection, user_id: Any, product_id: Any
    ) -> bool:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT 1 FROM reviews "
                "WHERE user_id = %s AND product_id = %s LIMIT 1",
                (user_id, product_id),
            )
            return cursor.fetchone() is not None
        finally:
            cursor.close()


    def create(
        self, conn: MySQLConnection, user_id: Any,
        product_id: Any, rating: Any, comment: str,
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO reviews (product_id, user_id, rating, comment)
                VALUES (%s, %s, %s, %s)
                """,
                (product_id, user_id, int(rating), comment.strip()),
            )
            return cursor.lastrowid
        finally:
            cursor.close()

review_repository = ReviewRepository()