from db.db_config import get_db_connection

class InventoryReportService:
    """
    Layanan untuk menangani semua logika bisnis yang terkait dengan laporan inventaris.
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

    def get_inventory_reports(self, start_date, end_date):
        """Mengambil laporan terkait inventaris."""
        conn = get_db_connection()
        
        total_value = conn.execute("""
            SELECT SUM(total_value) 
            FROM (
                SELECT p.price * p.stock as total_value FROM products p WHERE p.has_variants = 0
                UNION ALL 
                SELECT p.price * pv.stock as total_value FROM product_variants pv JOIN products p ON pv.product_id = p.id
            )
        """).fetchone()[0] or 0
        
        date_filter_orders, params_orders = self._get_date_filter_clause(start_date, end_date, 'o')
        date_filter_for_join = date_filter_orders.replace("WHERE o.status != 'Dibatalkan'", "")
        
        slow_moving = conn.execute(f"""
            SELECT p.name, p.stock, 
                   (SELECT COALESCE(SUM(oi.quantity), 0) FROM order_items oi JOIN orders o ON oi.order_id = o.id WHERE oi.product_id = p.id AND o.status != 'Dibatalkan' {date_filter_for_join}) AS total_sold
            FROM products p GROUP BY p.id ORDER BY total_sold ASC, p.stock DESC LIMIT 10
        """, params_orders).fetchall()

        low_stock = conn.execute("""
            SELECT name, stock, 'Produk Utama' as type, id as product_id, null as variant_id 
            FROM products WHERE has_variants = 0 AND stock <= 5 AND stock > 0 
            UNION ALL 
            SELECT p.name || ' (' || pv.size || ')' as name, pv.stock, 'Varian' as type, p.id as product_id, pv.id as variant_id 
            FROM product_variants pv JOIN products p ON pv.product_id = p.id WHERE pv.stock <= 5 AND pv.stock > 0 
            ORDER BY stock ASC
        """).fetchall()
        
        conn.close()
        return {'total_value': total_value, 'slow_moving': [dict(row) for row in slow_moving], 'low_stock': [dict(row) for row in low_stock]}

    def get_low_stock_chart_data(self, conn):
        """Mengambil data untuk grafik stok menipis."""
        low_stock_products_query = """
            SELECT name, stock, id as product_id FROM products WHERE has_variants = 0 AND stock <= 5 AND stock > 0
            UNION ALL
            SELECT p.name || ' (' || pv.size || ')' as name, pv.stock, p.id as product_id FROM product_variants pv JOIN products p ON pv.product_id = p.id WHERE pv.stock <= 5 AND pv.stock > 0
            ORDER BY stock ASC LIMIT 7
        """
        low_stock_products = conn.execute(low_stock_products_query).fetchall()
        return {
            'labels': [p['name'] for p in low_stock_products],
            'data': [p['stock'] for p in low_stock_products]
        }

    def get_inventory_low_stock_for_export(self):
        """Mengambil data stok menipis untuk diekspor."""
        conn = get_db_connection()
        query = """
            SELECT name, stock, 'Produk Utama' as type, id as product_id, null as variant_id, sku
            FROM products WHERE has_variants = 0 AND stock <= 5 AND stock > 0 
            UNION ALL 
            SELECT p.name || ' (' || pv.size || ')' as name, pv.stock, 'Varian' as type, p.id as product_id, pv.id as variant_id, pv.sku
            FROM product_variants pv JOIN products p ON pv.product_id = p.id WHERE pv.stock <= 5 AND pv.stock > 0 
            ORDER BY stock ASC
        """
        data = conn.execute(query).fetchall()
        conn.close()
        return data

    def get_inventory_slow_moving_for_export(self, start_date, end_date):
        """Mengambil data produk kurang laris untuk diekspor."""
        conn = get_db_connection()
        date_filter, params = self._get_date_filter_clause(start_date, end_date)
        date_filter_for_join = date_filter.replace("WHERE o.status != 'Dibatalkan'", "")
        query = f"""
            SELECT p.name, p.stock, 
                   (SELECT COALESCE(SUM(oi.quantity), 0) FROM order_items oi JOIN orders o ON oi.order_id = o.id WHERE oi.product_id = p.id AND o.status != 'Dibatalkan' {date_filter_for_join}) AS total_sold
            FROM products p GROUP BY p.id ORDER BY total_sold ASC, p.stock DESC LIMIT 20
        """
        data = conn.execute(query, params).fetchall()
        conn.close()
        return data

inventory_report_service = InventoryReportService()