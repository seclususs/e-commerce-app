from typing import Any, Dict, List, Optional

from mysql.connector.connection import MySQLConnection


class CategoryRepository:
    
    def find_all(self, conn: MySQLConnection) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM categories ORDER BY name ASC")
            return cursor.fetchall()
        finally:
            cursor.close()
            

    def find_by_id(
        self, conn: MySQLConnection, category_id: int
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM categories WHERE id = %s", (category_id,)
            )
            return cursor.fetchone()
        finally:
            cursor.close()


    def create(self, conn: MySQLConnection, name: str) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO categories (name) VALUES (%s)", (name.strip(),)
            )
            return cursor.lastrowid
        finally:
            cursor.close()


    def update(
        self, conn: MySQLConnection, category_id: int, name: str
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE categories SET name = %s WHERE id = %s",
                (name.strip(), category_id),
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def unlink_products(
        self, conn: MySQLConnection, category_id: int
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE products SET category_id = NULL WHERE category_id = %s",
                (category_id,),
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def delete(self, conn: MySQLConnection, category_id: int) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM categories WHERE id = %s", (category_id,)
            )
            return cursor.rowcount
        finally:
            cursor.close()

category_repository = CategoryRepository()