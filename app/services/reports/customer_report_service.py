from app.core.db import get_db_connection


class CustomerReportService:

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

    def get_customer_reports(self, start_date, end_date):
        conn = get_db_connection()
        date_filter, params = self._get_date_filter_clause(start_date, end_date)

        top_spenders = conn.execute(f"""
            SELECT u.username, u.email, SUM(o.total_amount) as total_spent FROM users u
            JOIN orders o ON u.id = o.user_id
            {date_filter}
            GROUP BY u.id ORDER BY total_spent DESC LIMIT 10
        """, params).fetchall()

        conn.close()
        return {'top_spenders': [dict(row) for row in top_spenders]}

    def get_cart_analytics(self, start_date, end_date):
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

    def get_full_customers_data_for_export(self, start_date, end_date):
        conn = get_db_connection()
        date_filter, params = self._get_date_filter_clause(start_date, end_date)
        query = f"""SELECT u.id, u.username, u.email, SUM(o.total_amount) as total_spent, COUNT(o.id) as order_count 
                     FROM users u JOIN orders o ON u.id = o.user_id {date_filter}
                     GROUP BY u.id ORDER BY total_spent DESC"""
        data = conn.execute(query, params).fetchall()
        conn.close()
        return data


customer_report_service = CustomerReportService()