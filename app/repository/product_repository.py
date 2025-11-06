import json
from typing import Any, Dict, List, Optional

from mysql.connector.connection import MySQLConnection


class ProductRepository:
    
    def find_by_id(
        self, conn: MySQLConnection, product_id: Any
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))
            product = cursor.fetchone()
            if product:
                try:
                    product["additional_image_urls"] = (
                        json.loads(product["additional_image_urls"])
                        if product["additional_image_urls"]
                        else []
                    )
                except (json.JSONDecodeError, TypeError):
                    product["additional_image_urls"] = []
            return product
        finally:
            cursor.close()


    def find_with_category(
        self, conn: MySQLConnection, product_id: Any
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT p.*, c.name AS category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.id = %s
                """,
                (product_id,),
            )
            return cursor.fetchone()
        finally:
            cursor.close()


    def create(
        self, conn: MySQLConnection, product_data: Dict[str, Any]
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO products (
                    name, price, discount_price, description, category_id,
                    colors, image_url, additional_image_urls, stock,
                    has_variants, weight_grams, sku
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    product_data["name"],
                    product_data["price"],
                    product_data.get("discount_price") or None,
                    product_data["description"],
                    product_data["category_id"],
                    product_data.get("colors"),
                    product_data["image_url"],
                    json.dumps(product_data["additional_image_urls"]),
                    product_data["stock"],
                    product_data["has_variants"],
                    product_data["weight_grams"],
                    product_data.get("sku"),
                ),
            )
            return cursor.lastrowid
        finally:
            cursor.close()


    def update(
        self, conn: MySQLConnection, product_id: Any, 
        update_data: Dict[str, Any],
    ) -> int:
        cursor = conn.cursor()
        try:
            additional_images_json = json.dumps(
                update_data.get("additional_image_urls", [])
            )
            cursor.execute(
                """
                UPDATE products SET
                    name=%s, price=%s, discount_price=%s, description=%s,
                    category_id=%s, colors=%s, stock=%s, image_url=%s,
                    additional_image_urls=%s, has_variants=%s,
                    weight_grams=%s, sku=%s
                WHERE id=%s
                """,
                (
                    update_data["name"],
                    update_data["price"],
                    update_data.get("discount_price") or None,
                    update_data["description"],
                    update_data["category_id"],
                    update_data.get("colors"),
                    update_data["stock"],
                    update_data["image_url"],
                    additional_images_json,
                    update_data["has_variants"],
                    update_data["weight_grams"],
                    update_data.get("sku"),
                    product_id,
                ),
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def delete(self, conn: MySQLConnection, product_id: Any) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
            return cursor.rowcount
        finally:
            cursor.close()


    def update_popularity(
        self, conn: MySQLConnection, product_id: Any
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE products SET popularity = popularity + 1 WHERE id = %s",
                (product_id,),
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def update_stock(
        self, conn: MySQLConnection, product_id: Any, total_stock: int
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE products SET stock = %s WHERE id = %s",
                (total_stock, product_id),
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def find_minimal_by_id(
        self, conn: MySQLConnection, product_id: int
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id, name, has_variants FROM products WHERE id = %s",
                (product_id,),
            )
            return cursor.fetchone()
        finally:
            cursor.close()


    def find_batch_minimal(
        self, conn: MySQLConnection, product_ids: List[int]
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            if not product_ids:
                return []
            placeholders = ", ".join(["%s"] * len(product_ids))
            query = (
                f"SELECT id, name, price, discount_price, image_url, "
                f"has_variants FROM products WHERE id IN ({placeholders})"
            )
            cursor.execute(query, tuple(product_ids))
            return cursor.fetchall()
        finally:
            cursor.close()


    def find_filtered(
        self, conn: MySQLConnection, filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            query_base = """
                SELECT
                    p.id, p.name, p.description, p.category_id, p.colors,
                    p.popularity, p.image_url, p.additional_image_urls,
                    p.stock, p.has_variants, p.weight_grams, p.sku,
                    c.name AS category_name,
                    IF(
                        p.has_variants,
                        MIN(COALESCE(pv.price, p.price)),
                        p.price
                    ) AS price,
                    IF(
                        p.has_variants,
                        MIN(COALESCE(pv.discount_price, p.discount_price)),
                        p.discount_price
                    ) AS discount_price
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                LEFT JOIN product_variants pv ON p.id = pv.product_id
            """
            
            params = []
            where_clauses = ["1=1"]

            if filters.get("search"):
                search_term = f"%{filters['search']}%"
                where_clauses.append(
                    "(p.name LIKE %s OR p.description LIKE %s "
                    "OR p.colors LIKE %s OR c.name LIKE %s)"
                )
                params.extend(
                    [search_term, search_term, search_term, search_term]
                )
            if filters.get("category"):
                where_clauses.append("p.category_id = %s")
                params.append(filters["category"])

            query_where = " WHERE " + " AND ".join(where_clauses)
            query_group = (
                " GROUP BY p.id, p.name, p.description, p.category_id, "
                "p.colors, p.popularity, p.image_url, "
                "p.additional_image_urls, p.stock, p.has_variants, "
                "p.weight_grams, p.sku, c.name"
            )
            
            sort_by = filters.get("sort", "popularity")
            order_query = ""
            if sort_by == "price_asc":
                order_query = """
                    ORDER BY COALESCE(
                        IF(p.has_variants, MIN(COALESCE(pv.discount_price, p.discount_price)), p.discount_price),
                        IF(p.has_variants, MIN(COALESCE(pv.price, p.price)), p.price)
                    ) ASC
                """
            elif sort_by == "price_desc":
                order_query = """
                    ORDER BY COALESCE(
                        IF(p.has_variants, MIN(COALESCE(pv.discount_price, p.discount_price)), p.discount_price),
                        IF(p.has_variants, MIN(COALESCE(pv.price, p.price)), p.price)
                    ) DESC
                """
            else:
                order_query = " ORDER BY p.popularity DESC"
            
            final_query = query_base + query_where + query_group + order_query
            cursor.execute(final_query, tuple(params))
            return cursor.fetchall()
        finally:
            cursor.close()


    def find_all_with_category(
        self, conn: MySQLConnection,
        search: Optional[str],
        category_id: Optional[Any],
        stock_status: Optional[str],
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            query_base = """
                SELECT
                    p.id, p.name, p.description, p.category_id, p.colors,
                    p.popularity, p.image_url, p.additional_image_urls,
                    p.stock, p.has_variants, p.weight_grams, p.sku,
                    c.name AS category_name,
                    IF(
                        p.has_variants,
                        MIN(COALESCE(pv.price, p.price)),
                        p.price
                    ) AS price,
                    IF(
                        p.has_variants,
                        MIN(COALESCE(pv.discount_price, p.discount_price)),
                        p.discount_price
                    ) AS discount_price
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                LEFT JOIN product_variants pv ON p.id = pv.product_id
            """
            
            params = []
            where_clauses = []
            if search:
                search_term = f"%{search}%"
                where_clauses.append("(p.name LIKE %s OR p.sku LIKE %s)")
                params.extend([search_term, search_term])
            if category_id:
                where_clauses.append("p.category_id = %s")
                params.append(category_id)
            if stock_status == "in_stock":
                where_clauses.append("p.stock > 5")
            elif stock_status == "low_stock":
                where_clauses.append("p.stock > 0 AND p.stock <= 5")
            elif stock_status == "out_of_stock":
                where_clauses.append("p.stock <= 0")
            
            query_where = ""
            if where_clauses:
                query_where = " WHERE " + " AND ".join(where_clauses)
            
            query_group = (
                " GROUP BY p.id, p.name, p.description, p.category_id, "
                "p.colors, p.popularity, p.image_url, "
                "p.additional_image_urls, p.stock, p.has_variants, "
                "p.weight_grams, p.sku, c.name"
            )
            query_order = " ORDER BY p.id DESC"
            
            final_query = query_base + query_where + query_group + query_order
            cursor.execute(final_query, tuple(params))
            return cursor.fetchall()
        finally:
            cursor.close()


    def find_related(
        self, conn: MySQLConnection, product_id: Any, category_id: Any
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
                SELECT p.*, c.name AS category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.category_id = %s AND p.id != %s
                ORDER BY p.popularity DESC
                LIMIT 4
            """
            cursor.execute(query, (category_id, product_id))
            return cursor.fetchall()
        finally:
            cursor.close()


    def delete_batch(self, conn: MySQLConnection, ids: List[Any]) -> int:
        cursor = conn.cursor()
        try:
            placeholders = ", ".join(["%s"] * len(ids))
            query = f"DELETE FROM products WHERE id IN ({placeholders})"
            cursor.execute(query, tuple(ids))
            return cursor.rowcount
        finally:
            cursor.close()


    def update_category_batch(
        self, conn: MySQLConnection, ids: List[Any], category_id: Any
    ) -> int:
        cursor = conn.cursor()
        try:
            placeholders = ", ".join(["%s"] * len(ids))
            params = (category_id,) + tuple(ids)
            query = (
                f"UPDATE products SET category_id = %s "
                f"WHERE id IN ({placeholders})"
            )
            cursor.execute(query, params)
            return cursor.rowcount
        finally:
            cursor.close()


    def update_stock_sku_weight_variant_status(
        self, conn: MySQLConnection, product_id: Any, 
        stock: int, weight_grams: int, 
        sku: Optional[str],  has_variants: bool,
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE products
                SET stock = %s, weight_grams = %s, sku = %s, has_variants = %s
                WHERE id = %s
                """,
                (stock, weight_grams, sku, has_variants, product_id),
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def get_stock(
        self, conn: MySQLConnection, product_id: int
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT stock FROM products WHERE id = %s", (product_id,)
            )
            return cursor.fetchone()
        finally:
            cursor.close()


    def increase_stock(
        self, conn: MySQLConnection, product_id: int, quantity: int
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE products SET stock = stock + %s WHERE id = %s",
                (quantity, product_id),
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def lock_stock(
        self, conn: MySQLConnection, product_id: int
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT stock FROM products WHERE id = %s FOR UPDATE",
                (product_id,),
            )
            return cursor.fetchone()
        finally:
            cursor.close()


    def decrease_stock(
        self, conn: MySQLConnection, product_id: int, quantity: int
    ) -> int:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE products SET stock = stock - %s WHERE id = %s",
                (quantity, product_id),
            )
            return cursor.rowcount
        finally:
            cursor.close()


    def find_batch_for_order(
        self, conn: MySQLConnection, product_ids: List[int]
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            placeholders = ", ".join(["%s"] * len(product_ids))
            cursor.execute(
                f"""
                SELECT id, name, price, discount_price
                FROM products WHERE id IN ({placeholders})
                """,
                tuple(product_ids),
            )
            return cursor.fetchall()
        finally:
            cursor.close()

product_repository = ProductRepository()