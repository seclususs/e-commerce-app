from db.db_config import get_db_connection
from datetime import datetime, timedelta

from .sales_report_service import sales_report_service
from .product_report_service import product_report_service
from .inventory_report_service import inventory_report_service
from .customer_report_service import customer_report_service


class ReportService:

    def get_dashboard_stats(self, start_date_str, end_date_str):
        conn = get_db_connection()
        try:
            total_sales = conn.execute("SELECT SUM(total_amount) FROM orders WHERE status != 'Dibatalkan' AND order_date BETWEEN ? AND ?", (start_date_str, end_date_str)).fetchone()[0]
            order_count = conn.execute("SELECT COUNT(id) FROM orders WHERE order_date BETWEEN ? AND ?", (start_date_str, end_date_str)).fetchone()[0]
            new_user_count = conn.execute("SELECT COUNT(id) FROM users WHERE created_at BETWEEN ? AND ?", (start_date_str, end_date_str)).fetchone()[0]
            product_count = conn.execute('SELECT COUNT(id) FROM products').fetchone()[0]

            sales_chart_data = sales_report_service.get_sales_chart_data(start_date_str, end_date_str, conn)
            top_products_chart = product_report_service.get_top_products_chart_data(start_date_str, end_date_str, conn)
            low_stock_chart = inventory_report_service.get_low_stock_chart_data(conn)

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

    def get_sales_summary(self, start_date, end_date):
        return sales_report_service.get_sales_summary(start_date, end_date)

    def get_voucher_effectiveness(self, start_date, end_date):
        return sales_report_service.get_voucher_effectiveness(start_date, end_date)

    def get_full_sales_data_for_export(self, start_date, end_date):
        return sales_report_service.get_full_sales_data_for_export(start_date, end_date)

    def get_full_vouchers_data_for_export(self, start_date, end_date):
        return sales_report_service.get_full_vouchers_data_for_export(start_date, end_date)

    def get_product_reports(self, start_date, end_date):
        return product_report_service.get_product_reports(start_date, end_date)

    def get_full_products_data_for_export(self, start_date, end_date):
        return product_report_service.get_full_products_data_for_export(start_date, end_date)

    def get_customer_reports(self, start_date, end_date):
        return customer_report_service.get_customer_reports(start_date, end_date)

    def get_cart_analytics(self, start_date, end_date):
        return customer_report_service.get_cart_analytics(start_date, end_date)

    def get_full_customers_data_for_export(self, start_date, end_date):
        return customer_report_service.get_full_customers_data_for_export(start_date, end_date)

    def get_inventory_reports(self, start_date, end_date):
        return inventory_report_service.get_inventory_reports(start_date, end_date)

    def get_inventory_low_stock_for_export(self):
        return inventory_report_service.get_inventory_low_stock_for_export()

    def get_inventory_slow_moving_for_export(self, start_date, end_date):
        return inventory_report_service.get_inventory_slow_moving_for_export(start_date, end_date)


report_service = ReportService()