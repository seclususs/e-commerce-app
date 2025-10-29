from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from mysql.connector.connection import MySQLConnection


class ReportRepository:

    def _get_date_filter_clause(
        self, start_date: Optional[str],
        end_date: Optional[str], 
        table_alias: str = "o",
    ) -> Tuple[str, List[str]]:
        date_filter = f" WHERE {table_alias}.status != 'Dibatalkan' "
        params: List[str] = []
        if start_date:
            date_filter += f" AND {table_alias}.order_date >= %s "
            params.append(start_date)
        if end_date:
            date_filter += f" AND {table_alias}.order_date <= %s "
            params.append(end_date)
        return date_filter, params

    def get_top_spenders(
        self, conn: MySQLConnection,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            date_filter, params = self._get_date_filter_clause(
                start_date, end_date
            )
            query = f"""
                SELECT
                    u.username,
                    u.email,
                    SUM(o.total_amount) AS total_spent
                FROM users u
                JOIN orders o ON u.id = o.user_id
                {date_filter}
                GROUP BY u.id
                ORDER BY total_spent DESC
                LIMIT 10
            """
            cursor.execute(query, tuple(params))
            return cursor.fetchall()
        finally:
            cursor.close()


    def get_cart_analytics_created(self, conn: MySQLConnection) -> int:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT COUNT(DISTINCT user_id) AS count FROM user_carts"
            )
            result = cursor.fetchone()
            return result["count"] or 0
        finally:
            cursor.close()


    def get_cart_analytics_completed(
        self, conn: MySQLConnection,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> int:
        cursor = conn.cursor(dictionary=True)
        try:
            date_filter, params = self._get_date_filter_clause(
                start_date, end_date
            )
            query = (
                "SELECT COUNT(DISTINCT user_id) AS count FROM orders o "
                f"{date_filter}"
            )
            cursor.execute(query, tuple(params))
            result = cursor.fetchone()
            return result["count"] or 0
        finally:
            cursor.close()


    def get_full_customers_data_for_export(
        self, conn: MySQLConnection,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            date_filter, params = self._get_date_filter_clause(
                start_date, end_date
            )
            query = f"""
                SELECT
                    u.id,
                    u.username,
                    u.email,
                    SUM(o.total_amount) AS total_spent,
                    COUNT(o.id) AS order_count
                FROM users u
                JOIN orders o ON u.id = o.user_id
                {date_filter}
                GROUP BY u.id
                ORDER BY total_spent DESC
            """
            cursor.execute(query, tuple(params))
            return cursor.fetchall()
        finally:
            cursor.close()


    def get_dashboard_sales(
        self, conn: MySQLConnection, start_date_str: str, end_date_str: str
    ) -> Decimal:
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
                SELECT SUM(total_amount) AS total
                FROM orders
                WHERE status != 'Dibatalkan'
                AND order_date BETWEEN %s AND %s
            """
            cursor.execute(query, (start_date_str, end_date_str))
            result = cursor.fetchone()
            return result["total"] or Decimal("0")
        finally:
            cursor.close()


    def get_dashboard_order_count(
        self, conn: MySQLConnection, start_date_str: str, end_date_str: str
    ) -> int:
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
                SELECT COUNT(id) AS count
                FROM orders
                WHERE order_date BETWEEN %s AND %s
            """
            cursor.execute(query, (start_date_str, end_date_str))
            result = cursor.fetchone()
            return result["count"] or 0
        finally:
            cursor.close()


    def get_dashboard_new_user_count(
        self, conn: MySQLConnection, start_date_str: str, end_date_str: str
    ) -> int:
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
                SELECT COUNT(id) AS count
                FROM users
                WHERE created_at BETWEEN %s AND %s
            """
            cursor.execute(query, (start_date_str, end_date_str))
            result = cursor.fetchone()
            return result["count"] or 0
        finally:
            cursor.close()


    def get_dashboard_product_count(self, conn: MySQLConnection) -> int:
        cursor = conn.cursor(dictionary=True)
        try:
            query = "SELECT COUNT(id) AS count FROM products"
            cursor.execute(query)
            result = cursor.fetchone()
            return result["count"] or 0
        finally:
            cursor.close()


    def get_inventory_total_value(
        self, conn: MySQLConnection
    ) -> Decimal:
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
                SELECT SUM(total_value) AS total_value
                FROM (
                    SELECT
                        (CASE
                            WHEN p.discount_price IS NOT NULL AND p.discount_price > 0
                            THEN p.discount_price
                            ELSE p.price
                        END) * p.stock AS total_value
                    FROM products p
                    WHERE p.has_variants = 0
                    UNION ALL
                    SELECT
                        (CASE
                            WHEN p.discount_price IS NOT NULL AND p.discount_price > 0
                            THEN p.discount_price
                            ELSE p.price
                        END) * pv.stock AS total_value
                    FROM product_variants pv
                    JOIN products p ON pv.product_id = p.id
                ) AS inventory_values
            """
            cursor.execute(query)
            result = cursor.fetchone()
            return result["total_value"] or Decimal("0")
        finally:
            cursor.close()


    def get_inventory_slow_moving(
        self, conn: MySQLConnection,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            date_filter, params = self._get_date_filter_clause(
                start_date, end_date, "o"
            )
            date_filter_for_join = date_filter.replace(
                "WHERE o.status != 'Dibatalkan'", ""
            )
            query = f"""
                SELECT
                    p.name,
                    p.stock,
                    (
                        SELECT COALESCE(SUM(oi.quantity), 0)
                        FROM order_items oi
                        JOIN orders o ON oi.order_id = o.id
                        WHERE oi.product_id = p.id
                        AND o.status != 'Dibatalkan'
                        {date_filter_for_join}
                    ) AS total_sold
                FROM products p
                GROUP BY p.id
                ORDER BY total_sold ASC, p.stock DESC
                LIMIT 10
            """
            cursor.execute(query, tuple(params))
            return cursor.fetchall()
        finally:
            cursor.close()


    def get_inventory_low_stock(
        self, conn: MySQLConnection
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
                SELECT
                    name,
                    stock,
                    'Produk Utama' AS type,
                    id AS product_id,
                    NULL AS variant_id
                FROM products
                WHERE has_variants = 0
                AND stock <= 5
                AND stock > 0
                UNION ALL
                SELECT
                    CONCAT(p.name, ' (', pv.size, ')') AS name,
                    pv.stock,
                    'Varian' AS type,
                    p.id AS product_id,
                    pv.id AS variant_id
                FROM product_variants pv
                JOIN products p ON pv.product_id = p.id
                WHERE pv.stock <= 5
                AND pv.stock > 0
                ORDER BY stock ASC
            """
            cursor.execute(query)
            return cursor.fetchall()
        finally:
            cursor.close()


    def get_low_stock_chart_data(
        self, conn: MySQLConnection
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
                SELECT
                    name,
                    stock,
                    id AS product_id
                FROM products
                WHERE has_variants = 0
                AND stock <= 5
                AND stock > 0
                UNION ALL
                SELECT
                    CONCAT(p.name, ' (', pv.size, ')') AS name,
                    pv.stock,
                    p.id AS product_id
                FROM product_variants pv
                JOIN products p ON pv.product_id = p.id
                WHERE pv.stock <= 5
                AND pv.stock > 0
                ORDER BY stock ASC
                LIMIT 7
            """
            cursor.execute(query)
            return cursor.fetchall()
        finally:
            cursor.close()


    def get_inventory_low_stock_for_export(
        self, conn: MySQLConnection
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
                SELECT
                    name,
                    stock,
                    'Produk Utama' AS type,
                    id AS product_id,
                    NULL AS variant_id,
                    sku
                FROM products
                WHERE has_variants = 0
                AND stock <= 5
                AND stock > 0
                UNION ALL
                SELECT
                    CONCAT(p.name, ' (', pv.size, ')') AS name,
                    pv.stock,
                    'Varian' AS type,
                    p.id AS product_id,
                    pv.id AS variant_id,
                    pv.sku
                FROM product_variants pv
                JOIN products p ON pv.product_id = p.id
                WHERE pv.stock <= 5
                AND pv.stock > 0
                ORDER BY stock ASC
            """
            cursor.execute(query)
            return cursor.fetchall()
        finally:
            cursor.close()


    def get_inventory_slow_moving_for_export(
        self, conn: MySQLConnection,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            date_filter, params = self._get_date_filter_clause(
                start_date, end_date
            )
            date_filter_for_join = date_filter.replace(
                "WHERE o.status != 'Dibatalkan'", ""
            )
            query = f"""
                SELECT
                    p.name,
                    p.stock,
                    (
                        SELECT COALESCE(SUM(oi.quantity), 0)
                        FROM order_items oi
                        JOIN orders o ON oi.order_id = o.id
                        WHERE oi.product_id = p.id
                        AND o.status != 'Dibatalkan'
                        {date_filter_for_join}
                    ) AS total_sold
                FROM products p
                GROUP BY p.id
                ORDER BY total_sold ASC, p.stock DESC
                LIMIT 20
            """
            cursor.execute(query, tuple(params))
            return cursor.fetchall()
        finally:
            cursor.close()


    def get_top_selling_products(
        self, conn: MySQLConnection,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            date_filter, params = self._get_date_filter_clause(
                start_date, end_date
            )
            query = f"""
                SELECT p.name, SUM(oi.quantity) AS total_sold
                FROM products p
                JOIN order_items oi ON p.id = oi.product_id
                JOIN orders o ON oi.order_id = o.id
                {date_filter}
                GROUP BY p.id
                ORDER BY total_sold DESC
                LIMIT 10
            """
            cursor.execute(query, tuple(params))
            return cursor.fetchall()
        finally:
            cursor.close()


    def get_most_viewed_products(
        self, conn: MySQLConnection
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
                SELECT name, popularity
                FROM products
                ORDER BY popularity DESC
                LIMIT 10
            """
            cursor.execute(query)
            return cursor.fetchall()
        finally:
            cursor.close()


    def get_top_products_chart_data(
        self, conn: MySQLConnection, start_date_str: str, end_date_str: str
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
                SELECT p.name, SUM(oi.quantity) AS total_sold
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                JOIN orders o ON oi.order_id = o.id
                WHERE o.status != 'Dibatalkan'
                AND o.order_date BETWEEN %s AND %s
                GROUP BY p.id
                ORDER BY total_sold DESC
                LIMIT 5
            """
            cursor.execute(query, (start_date_str, end_date_str))
            return cursor.fetchall()
        finally:
            cursor.close()


    def get_full_products_data_for_export(
        self, conn: MySQLConnection,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            date_filter, params = self._get_date_filter_clause(
                start_date, end_date
            )
            date_filter_for_join = date_filter.replace(
                "WHERE o.status != 'Dibatalkan'", ""
            )
            query = f"""
                SELECT
                    p.id,
                    p.name,
                    c.name AS category_name,
                    p.sku,
                    p.price,
                    p.discount_price,
                    p.stock,
                    (
                        SELECT COALESCE(SUM(oi.quantity), 0)
                        FROM order_items oi
                        JOIN orders o ON oi.order_id = o.id
                        WHERE oi.product_id = p.id
                        AND o.status != 'Dibatalkan'
                        {date_filter_for_join}
                    ) AS total_sold,
                    p.popularity
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                GROUP BY p.id
                ORDER BY total_sold DESC
            """
            cursor.execute(query, tuple(params))
            return cursor.fetchall()
        finally:
            cursor.close()


    def get_sales_summary(
        self, conn: MySQLConnection,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            date_filter, params = self._get_date_filter_clause(
                start_date, end_date
            )
            query = f"""
                SELECT
                    COALESCE(SUM(o.total_amount), 0) AS total_revenue,
                    COUNT(o.id) AS total_orders,
                    COALESCE(SUM(oi.quantity), 0) AS total_items_sold
                FROM orders o
                LEFT JOIN order_items oi ON o.id = oi.order_id
                {date_filter}
            """
            cursor.execute(query, tuple(params))
            return cursor.fetchone()
        finally:
            cursor.close()


    def get_voucher_effectiveness(
        self, conn: MySQLConnection,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            date_filter, params = self._get_date_filter_clause(
                start_date, end_date
            )
            date_filter_and = date_filter.replace("WHERE", "AND")
            query = f"""
                SELECT
                    voucher_code,
                    COUNT(id) AS usage_count,
                    SUM(discount_amount) AS total_discount
                FROM orders o
                WHERE voucher_code IS NOT NULL {date_filter_and}
                GROUP BY voucher_code
                ORDER BY usage_count DESC;
            """
            cursor.execute(query, tuple(params))
            return cursor.fetchall()
        finally:
            cursor.close()


    def get_sales_chart_data(
        self, conn: MySQLConnection, start_date_str: str, end_date_str: str
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            query = """
                SELECT
                    DATE(order_date) AS sale_date,
                    SUM(total_amount) AS daily_total
                FROM orders
                WHERE status != 'Dibatalkan' AND order_date BETWEEN %s AND %s
                GROUP BY sale_date
                ORDER BY sale_date ASC
            """
            cursor.execute(query, (start_date_str, end_date_str))
            return cursor.fetchall()
        finally:
            cursor.close()


    def get_full_sales_data_for_export(
        self, conn: MySQLConnection,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            date_filter, params = self._get_date_filter_clause(
                start_date, end_date
            )
            query = f"""
                SELECT
                    o.id,
                    o.order_date,
                    o.shipping_name,
                    u.email,
                    o.subtotal,
                    o.discount_amount,
                    o.shipping_cost,
                    o.total_amount,
                    o.status,
                    o.payment_method,
                    o.voucher_code
                FROM orders o
                LEFT JOIN users u ON o.user_id = u.id
                {date_filter}
                ORDER BY o.order_date DESC
            """
            cursor.execute(query, tuple(params))
            return cursor.fetchall()
        finally:
            cursor.close()


    def get_full_vouchers_data_for_export(
        self, conn: MySQLConnection,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor(dictionary=True)
        try:
            date_filter, params = self._get_date_filter_clause(
                start_date, end_date
            )
            date_filter_voucher = date_filter.replace(
                "WHERE o.status != 'Dibatalkan'", ""
            )
            query = f"""
                SELECT
                    v.code,
                    v.type,
                    v.value,
                    (
                        SELECT COUNT(o.id)
                        FROM orders o
                        WHERE o.voucher_code = v.code
                        AND o.status != 'Dibatalkan' {date_filter_voucher}
                    ) AS usage_count,
                    (
                        SELECT COALESCE(SUM(o.discount_amount), 0)
                        FROM orders o
                        WHERE o.voucher_code = v.code
                        AND o.status != 'Dibatalkan' {date_filter_voucher}
                    ) AS total_discount
                FROM vouchers v
                ORDER BY usage_count DESC
            """
            cursor.execute(query, tuple(params * 2))
            return cursor.fetchall()
        finally:
            cursor.close()

report_repository = ReportRepository()