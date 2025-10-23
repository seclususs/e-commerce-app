from app.core.db import get_db_connection
from datetime import datetime, timedelta


class SalesReportService:

    def _get_date_filter_clause(self, start_date, end_date, table_alias='o'):
        date_filter = f" WHERE {table_alias}.status != 'Dibatalkan' "
        params = []
        if start_date:
            date_filter += f" AND {table_alias}.order_date >= ? "
            params.append(start_date)
        if end_date:
            date_filter += f" AND {table_alias}.order_date <= ? "
            params.append(end_date)
        return date_filter, params

    def get_sales_summary(self, start_date, end_date):
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

    def get_voucher_effectiveness(self, start_date, end_date):
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

    def get_sales_chart_data(self, start_date_str, end_date_str, conn):
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

    def get_full_sales_data_for_export(self, start_date, end_date):
        conn = get_db_connection()
        date_filter, params = self._get_date_filter_clause(start_date, end_date)
        query = f"""SELECT o.id, o.order_date, o.shipping_name, u.email, o.subtotal, o.discount_amount, o.shipping_cost, o.total_amount, o.status, o.payment_method, o.voucher_code 
                     FROM orders o LEFT JOIN users u ON o.user_id = u.id {date_filter} ORDER BY o.order_date DESC"""
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


sales_report_service = SalesReportService()