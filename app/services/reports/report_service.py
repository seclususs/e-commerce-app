from db.db_config import get_db_connection
from datetime import datetime, timedelta

class ReportService:
    """
    Layanan untuk menampung semua query SQL kompleks untuk pembuatan laporan.
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

    def get_dashboard_stats(self, start_date_str, end_date_str):
        """Mengambil semua data statistik yang diperlukan untuk halaman dashboard."""
        conn = get_db_connection()
        try:
            total_sales = conn.execute("SELECT SUM(total_amount) FROM orders WHERE status != 'Dibatalkan' AND order_date BETWEEN ? AND ?", (start_date_str, end_date_str)).fetchone()[0]
            order_count = conn.execute("SELECT COUNT(id) FROM orders WHERE order_date BETWEEN ? AND ?", (start_date_str, end_date_str)).fetchone()[0]
            new_user_count = conn.execute("SELECT COUNT(id) FROM users WHERE created_at BETWEEN ? AND ?", (start_date_str, end_date_str)).fetchone()[0]
            product_count = conn.execute('SELECT COUNT(id) FROM products').fetchone()[0]

            sales_chart_data = self._get_sales_chart_data(start_date_str, end_date_str, conn)
            top_products_chart = self._get_top_products_chart_data(start_date_str, end_date_str, conn)
            low_stock_chart = self._get_low_stock_chart_data(conn)

            return {
                'total_sales': total_sales or 0,
                'order_count': order_count or 0,
                'new_user_count': new_user_count or 0,
                'product_count': product_count or 0,
                'sales_chart_data': sales_chart_data,
                'top_products_chart': top_products_chart,
                'low_stock_chart': low_stock_chart
            }
        finally:
            conn.close()

    def _get_sales_chart_data(self, start_date_str, end_date_str, conn):
        """Mengambil data mentah untuk grafik penjualan harian."""
        sales_data_raw = conn.execute("""
            SELECT date(order_date) as sale_date, SUM(total_amount) as daily_total
            FROM orders WHERE status != 'Dibatalkan' AND order_date BETWEEN ? AND ?
            GROUP BY sale_date ORDER BY sale_date ASC
        """, (start_date_str, end_date_str)).fetchall()
        
        sales_by_date = {row['sale_date']: row['daily_total'] for row in sales_data_raw}
        labels, data = [], []
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d %H:%M:%S').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S').date()
        delta = end_date - start_date

        for i in range(delta.days + 1):
            current_date = start_date + timedelta(days=i)
            date_str = current_date.strftime('%Y-%m-%d')
            labels.append(current_date.strftime('%d %b'))
            data.append(sales_by_date.get(date_str, 0))
        
        return {'labels': labels, 'data': data}

    def _get_top_products_chart_data(self, start_date_str, end_date_str, conn):
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

    def _get_low_stock_chart_data(self, conn):
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
    
    def get_sales_summary(self, start_date, end_date):
        """Mengambil ringkasan data penjualan."""
        conn = get_db_connection()
        date_filter, params = self._get_date_filter_clause(start_date, end_date)
        query = f"""SELECT 
                        COALESCE(SUM(o.total_amount), 0) as total_revenue, 
                        COUNT(o.id) as total_orders, 
                        COALESCE(SUM(oi.quantity), 0) as total_items_sold
                     FROM orders o
                     LEFT JOIN order_items oi ON o.id = oi.order_id
                     {date_filter}"""
        report = conn.execute(query, params).fetchone()
        conn.close()
        return dict(report)

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
        return {'top_selling': top_selling, 'most_viewed': most_viewed}

    def get_customer_reports(self, start_date, end_date):
        """Mengambil laporan terkait pelanggan."""
        conn = get_db_connection()
        date_filter, params = self._get_date_filter_clause(start_date, end_date)
        
        top_spenders = conn.execute(f"""
            SELECT u.username, u.email, SUM(o.total_amount) as total_spent FROM users u
            JOIN orders o ON u.id = o.user_id
            {date_filter}
            GROUP BY u.id ORDER BY total_spent DESC LIMIT 10
        """, params).fetchall()
        
        conn.close()
        return {'top_spenders': top_spenders}

    def get_voucher_effectiveness(self, start_date, end_date):
        """Mengambil laporan efektivitas voucher."""
        conn = get_db_connection()
        date_filter, params = self._get_date_filter_clause(start_date, end_date)
        date_filter_and = date_filter.replace('WHERE', 'AND')

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
        report = conn.execute(query, params).fetchall()
        conn.close()
        return report

    def get_cart_analytics(self, start_date, end_date):
        """Mengambil data analitik keranjang belanja."""
        conn = get_db_connection()
        date_filter, params = self._get_date_filter_clause(start_date, end_date)
        
        total_carts_created = conn.execute("SELECT COUNT(DISTINCT user_id) FROM user_carts").fetchone()[0] or 0
        total_orders_completed = conn.execute(f"SELECT COUNT(DISTINCT user_id) FROM orders o {date_filter}", params).fetchone()[0] or 0
        
        abandonment_rate = (1 - (total_orders_completed / total_carts_created)) * 100 if total_carts_created > 0 else 0
        
        conn.close()
        return {
            'abandonment_rate': round(abandonment_rate, 2),
            'carts_created': total_carts_created,
            'orders_completed': total_orders_completed
        }
        
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
        
        # Filter untuk join, perlu alias berbeda jika ada
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
        return {'total_value': total_value, 'slow_moving': slow_moving, 'low_stock': low_stock}

    def get_full_sales_data_for_export(self, start_date, end_date):
        conn = get_db_connection()
        date_filter, params = self._get_date_filter_clause(start_date, end_date)
        query = f"""SELECT o.id, o.order_date, o.shipping_name, u.email, o.subtotal, o.discount_amount, o.shipping_cost, o.total_amount, o.status, o.payment_method, o.voucher_code 
                     FROM orders o LEFT JOIN users u ON o.user_id = u.id {date_filter} ORDER BY o.order_date DESC"""
        data = conn.execute(query, params).fetchall()
        conn.close()
        return data

    def get_full_products_data_for_export(self, start_date, end_date):
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
        
    def get_full_customers_data_for_export(self, start_date, end_date):
        conn = get_db_connection()
        date_filter, params = self._get_date_filter_clause(start_date, end_date)
        query = f"""SELECT u.id, u.username, u.email, SUM(o.total_amount) as total_spent, COUNT(o.id) as order_count 
                     FROM users u JOIN orders o ON u.id = o.user_id {date_filter}
                     GROUP BY u.id ORDER BY total_spent DESC"""
        data = conn.execute(query, params).fetchall()
        conn.close()
        return data
        
    def get_inventory_low_stock_for_export(self):
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

    def get_full_vouchers_data_for_export(self, start_date, end_date):
        conn = get_db_connection()
        date_filter, params = self._get_date_filter_clause(start_date, end_date)
        date_filter_voucher = date_filter.replace("WHERE o.status != 'Dibatalkan'", "")
        query = f"""
            SELECT 
                v.code, v.type, v.value,
                (SELECT COUNT(o.id) FROM orders o WHERE o.voucher_code = v.code AND o.status != 'Dibatalkan' {date_filter_voucher}) as usage_count,
                (SELECT COALESCE(SUM(o.discount_amount), 0) FROM orders o WHERE o.voucher_code = v.code AND o.status != 'Dibatalkan' {date_filter_voucher}) as total_discount
            FROM vouchers v ORDER BY usage_count DESC
        """
        data = conn.execute(query, params * 2).fetchall()
        conn.close()
        return data

report_service = ReportService()