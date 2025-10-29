from typing import Any, Dict, List, Optional

from mysql.connector.connection import MySQLConnection


class CartRepository:
    
    def get_user_cart_items(
        self, conn: MySQLConnection, user_id: int
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
                SELECT
                    p.id, p.name, p.price, p.discount_price, p.image_url,
                    p.has_variants, uc.quantity, uc.variant_id,
                    uc.id as cart_item_id, pv.size
                FROM user_carts uc
                JOIN products p ON uc.product_id = p.id
                LEFT JOIN product_variants pv ON uc.variant_id = pv.id
                WHERE uc.user_id = %s
            """
            cursor.execute(query, (user_id,))
            return cursor.fetchall()
        finally:
            cursor.close()


    def find_cart_item(
        self,
        conn: MySQLConnection,
        user_id: int,
        product_id: int,
        variant_id: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            if variant_id is None:
                query = (
                    "SELECT id, quantity FROM user_carts "
                    "WHERE user_id = %s AND product_id = %s "
                    "AND variant_id IS NULL"
                )
                params = (user_id, product_id)
            else:
                query = (
                    "SELECT id, quantity FROM user_carts "
                    "WHERE user_id = %s AND product_id = %s AND variant_id = %s"
                )
                params = (user_id, product_id, variant_id)
            cursor.execute(query, params)
            return cursor.fetchone()
        finally:
            cursor.close()


    def update_cart_quantity(
        self, conn: MySQLConnection, cart_item_id: int, quantity: int
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE user_carts SET quantity = %s WHERE id = %s",
                (quantity, cart_item_id),
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def create_cart_item(
        self,
        conn: MySQLConnection,
        user_id: int,
        product_id: int,
        variant_id: Optional[int],
        quantity: int,
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO user_carts
                (user_id, product_id, variant_id, quantity)
                VALUES (%s, %s, %s, %s)
                """,
                (user_id, product_id, variant_id, quantity),
            )
            return cursor.lastrowid
        finally:
            cursor.close()


    def delete_cart_item(self, conn: MySQLConnection, cart_item_id: int) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM user_carts WHERE id = %s", (cart_item_id,)
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def clear_user_cart(self, conn: MySQLConnection, user_id: int) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM user_carts WHERE user_id = %s", (user_id,)
            )
            return cursor.rowcount
        finally:
            cursor.close()

cart_repository = CartRepository()