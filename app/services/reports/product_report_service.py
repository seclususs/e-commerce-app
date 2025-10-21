from db.db_config import get_db_connection

class ProductReportService:
    """
    Layanan untuk menangani semua logika bisnis yang terkait dengan laporan produk.
    """

    def _get_date_filter_clause(self, start_date, end_date, table_alias='o'):
        """Helper untuk membuat klausa filter tanggal."""
        date_filter = f" WHERE {table_alias}.status != 'Dibatalkan' "
        params = []
        if start_date:
            date_filter += f" AND {table_alias}.order_date >= ? "
            params.append(start_date)
        if end_date:
            date_filter += f" AND {table_alias}.order_date <= ? "
            params.append(end_date)
        return date_filter, params

    def get_product_reports(self, start_date, end_date):
        """Mengambil laporan terkait produk."""
        conn = get_db_connection()
        date_filter, params = self._get_date_filter_clause(start_date, end_date)
        
        top_selling = conn.execute(f"""
            SELECT p.name, SUM(oi.quantity) as total_sold FROM products p
            JOIN order_items oi ON p.id = oi.product_id
            JOIN orders o ON oi.order_id = o.id
            {date_filter}
            GROUP BY p.id ORDER BY total_sold DESC LIMIT 10
        """, params).fetchall()
        
        most_viewed = conn.execute("SELECT name, popularity FROM products ORDER BY popularity DESC LIMIT 10").fetchall()
        
        conn.close()
        return {'top_selling': [dict(row) for row in top_selling], 'most_viewed': [dict(row) for row in most_viewed]}
        
    def get_top_products_chart_data(self, start_date_str, end_date_str, conn):
        """Mengambil data untuk grafik produk terlaris."""
        top_products = conn.execute("""
            SELECT p.name, SUM(oi.quantity) as total_sold
            FROM order_items oi JOIN products p ON oi.product_id = p.id JOIN orders o ON oi.order_id = o.id
            WHERE o.status != 'Dibatalkan' AND o.order_date BETWEEN ? AND ?
            GROUP BY p.id ORDER BY total_sold DESC LIMIT 5
        """, (start_date_str, end_date_str)).fetchall()
        return {
            'labels': [p['name'] for p in top_products],
            'data': [p['total_sold'] for p in top_products]
        }
        
    def get_full_products_data_for_export(self, start_date, end_date):
        """Mengambil data produk lengkap untuk diekspor."""
        conn = get_db_connection()
        date_filter, params = self._get_date_filter_clause(start_date, end_date)
        date_filter_for_join = date_filter.replace("WHERE o.status != 'Dibatalkan'", "")
        query = f"""
            SELECT p.id, p.name, c.name as category_name, p.sku, p.price, p.discount_price, p.stock,
                   (SELECT COALESCE(SUM(oi.quantity), 0) FROM order_items oi JOIN orders o ON oi.order_id = o.id WHERE oi.product_id = p.id AND o.status != 'Dibatalkan' {date_filter_for_join}) as total_sold,
                   p.popularity
            FROM products p LEFT JOIN categories c ON p.category_id = c.id
            GROUP BY p.id ORDER BY total_sold DESC
        """
        data = conn.execute(query, params).fetchall()
        conn.close()
        return data

product_report_service = ProductReportService()