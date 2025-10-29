from mysql.connector.connection import MySQLConnection
from typing import Any, Dict, List, Optional


class VariantRepository:

    def find_by_product_id(
        self, conn: MySQLConnection, product_id: Any
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM product_variants "
                "WHERE product_id = %s ORDER BY id",
                (product_id,),
            )
            return cursor.fetchall()
        finally:
            cursor.close()


    def find_by_id(
        self, conn: MySQLConnection, variant_id: int
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM product_variants WHERE id = %s", (variant_id,)
            )
            return cursor.fetchone()
        finally:
            cursor.close()


    def create(
        self, conn: MySQLConnection,
        product_id: Any, size: str,
        stock: int, weight_grams: int,
        sku: Optional[str],
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO product_variants
                (product_id, size, stock, weight_grams, sku)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (product_id, size.upper().strip(), stock, weight_grams, sku),
            )
            return cursor.lastrowid
        finally:
            cursor.close()


    def update(
        self, conn: MySQLConnection,
        variant_id: Any, product_id: Any,
        size: str, stock: int, weight_grams: int,
        sku: Optional[str],
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE product_variants
                SET size = %s, stock = %s, weight_grams = %s, sku = %s
                WHERE id = %s AND product_id = %s
                """,
                (
                    size.upper().strip(),
                    stock,
                    weight_grams,
                    sku,
                    variant_id,
                    product_id,
                ),
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def delete(
        self, conn: MySQLConnection, variant_id: Any, product_id: Any
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM product_variants WHERE id = %s AND product_id = %s",
                (variant_id, product_id),
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def delete_by_product_id(
        self, conn: MySQLConnection, product_id: Any
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM product_variants WHERE product_id = %s",
                (product_id,),
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def get_total_stock(self, conn: MySQLConnection, product_id: Any) -> int:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT SUM(stock) AS total FROM product_variants "
                "WHERE product_id = %s",
                (product_id,),
            )
            total_stock_row = cursor.fetchone()
            return (
                total_stock_row["total"]
                if total_stock_row and total_stock_row["total"] is not None
                else 0
            )
        finally:
            cursor.close()


    def check_exists(
        self, conn: MySQLConnection, variant_id: int, product_id: int
    ) -> bool:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT 1 FROM product_variants "
                "WHERE id = %s AND product_id = %s",
                (variant_id, product_id),
            )
            return cursor.fetchone() is not None
        finally:
            cursor.close()


    def find_batch_minimal(
        self, conn: MySQLConnection, variant_ids: List[int]
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            if not variant_ids:
                return []
            placeholders = ", ".join(["%s"] * len(variant_ids))
            query = (
                f"SELECT id, product_id, size FROM product_variants "
                f"WHERE id IN ({placeholders})"
            )
            cursor.execute(query, tuple(variant_ids))
            return cursor.fetchall()
        finally:
            cursor.close()


    def get_stock(
        self, conn: MySQLConnection, variant_id: int
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT stock FROM product_variants WHERE id = %s",
                (variant_id,),
            )
            return cursor.fetchone()
        finally:
            cursor.close()


    def increase_stock(
        self, conn: MySQLConnection, variant_id: int, quantity: int
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE product_variants SET stock = stock + %s WHERE id = %s",
                (quantity, variant_id),
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def lock_stock(
        self, conn: MySQLConnection, variant_id: int
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT stock FROM product_variants WHERE id = %s FOR UPDATE",
                (variant_id,),
            )
            return cursor.fetchone()
        finally:
            cursor.close()


    def decrease_stock(
        self, conn: MySQLConnection, variant_id: int, quantity: int
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE product_variants SET stock = stock - %s WHERE id = %s",
                (quantity, variant_id),
            )
            return cursor.rowcount
        finally:
            cursor.close()

variant_repository = VariantRepository()