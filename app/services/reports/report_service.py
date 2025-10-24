from app.core.db import get_db_connection
from datetime import datetime, timedelta
from app.utils.logging_utils import get_logger
from .sales_report_service import sales_report_service
from .product_report_service import product_report_service
from .inventory_report_service import inventory_report_service
from .customer_report_service import customer_report_service

logger = get_logger(__name__)


class ReportService:


    def get_dashboard_stats(self, start_date_str, end_date_str):
        logger.info(f"Mengambil statistik dasbor untuk periode: {start_date_str} hingga {end_date_str}")

        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            query_sales = """
                SELECT SUM(total_amount) AS total
                FROM orders
                WHERE status != 'Dibatalkan'
                AND order_date BETWEEN %s AND %s
            """
            cursor.execute(query_sales, (start_date_str, end_date_str))
            total_sales = cursor.fetchone()['total'] or 0
            logger.debug(f"Total penjualan dihitung: {total_sales}")

            query_orders = """
                SELECT COUNT(id) AS count
                FROM orders
                WHERE order_date BETWEEN %s AND %s
            """
            cursor.execute(query_orders, (start_date_str, end_date_str))
            order_count = cursor.fetchone()['count'] or 0
            logger.debug(f"Jumlah pesanan dihitung: {order_count}")

            query_users = """
                SELECT COUNT(id) AS count
                FROM users
                WHERE created_at BETWEEN %s AND %s
            """
            cursor.execute(query_users, (start_date_str, end_date_str))
            new_user_count = cursor.fetchone()['count'] or 0
            logger.debug(f"Jumlah pengguna baru dihitung: {new_user_count}")

            query_products = "SELECT COUNT(id) AS count FROM products"
            cursor.execute(query_products)
            product_count = cursor.fetchone()['count'] or 0
            logger.debug(f"Jumlah total produk dihitung: {product_count}")

            logger.debug("Mengambil data grafik...")
            sales_chart_data = sales_report_service.get_sales_chart_data(start_date_str, end_date_str, conn)
            top_products_chart = product_report_service.get_top_products_chart_data(start_date_str, end_date_str, conn)
            low_stock_chart = inventory_report_service.get_low_stock_chart_data(conn)
            logger.debug("Data grafik diambil.")

            stats = {
                'total_sales': total_sales,
                'order_count': order_count,
                'new_user_count': new_user_count,
                'product_count': product_count,
                'sales_chart_data': sales_chart_data,
                'top_products_chart': top_products_chart,
                'low_stock_chart': low_stock_chart
            }

            logger.info("Pengambilan statistik dasbor selesai.")
            return stats

        except Exception as e:
            logger.error(f"Kesalahan saat mengambil statistik dasbor: {e}", exc_info=True)
            raise

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug("Koneksi database ditutup untuk get_dashboard_stats.")


    def get_sales_summary(self, start_date, end_date):
        logger.debug(f"Memanggil sales_report_service.get_sales_summary untuk periode: {start_date} hingga {end_date}")
        return sales_report_service.get_sales_summary(start_date, end_date)


    def get_voucher_effectiveness(self, start_date, end_date):
        logger.debug(f"Memanggil sales_report_service.get_voucher_effectiveness untuk periode: {start_date} hingga {end_date}")
        return sales_report_service.get_voucher_effectiveness(start_date, end_date)


    def get_full_sales_data_for_export(self, start_date, end_date):
        logger.debug(f"Memanggil sales_report_service.get_full_sales_data_for_export untuk periode: {start_date} hingga {end_date}")
        return sales_report_service.get_full_sales_data_for_export(start_date, end_date)


    def get_full_vouchers_data_for_export(self, start_date, end_date):
        logger.debug(f"Memanggil sales_report_service.get_full_vouchers_data_for_export untuk periode: {start_date} hingga {end_date}")
        return sales_report_service.get_full_vouchers_data_for_export(start_date, end_date)


    def get_product_reports(self, start_date, end_date):
        logger.debug(f"Memanggil product_report_service.get_product_reports untuk periode: {start_date} hingga {end_date}")
        return product_report_service.get_product_reports(start_date, end_date)


    def get_full_products_data_for_export(self, start_date, end_date):
        logger.debug(f"Memanggil product_report_service.get_full_products_data_for_export untuk periode: {start_date} hingga {end_date}")
        return product_report_service.get_full_products_data_for_export(start_date, end_date)


    def get_customer_reports(self, start_date, end_date):
        logger.debug(f"Memanggil customer_report_service.get_customer_reports untuk periode: {start_date} hingga {end_date}")
        return customer_report_service.get_customer_reports(start_date, end_date)


    def get_cart_analytics(self, start_date, end_date):
        logger.debug(f"Memanggil customer_report_service.get_cart_analytics untuk periode: {start_date} hingga {end_date}")
        return customer_report_service.get_cart_analytics(start_date, end_date)


    def get_full_customers_data_for_export(self, start_date, end_date):
        logger.debug(f"Memanggil customer_report_service.get_full_customers_data_for_export untuk periode: {start_date} hingga {end_date}")
        return customer_report_service.get_full_customers_data_for_export(start_date, end_date)


    def get_inventory_reports(self, start_date, end_date):
        logger.debug(f"Memanggil inventory_report_service.get_inventory_reports untuk periode: {start_date} hingga {end_date}")
        return inventory_report_service.get_inventory_reports(start_date, end_date)


    def get_inventory_low_stock_for_export(self):
        logger.debug("Memanggil inventory_report_service.get_inventory_low_stock_for_export")
        return inventory_report_service.get_inventory_low_stock_for_export()


    def get_inventory_slow_moving_for_export(self, start_date, end_date):
        logger.debug(f"Memanggil inventory_report_service.get_inventory_slow_moving_for_export untuk periode: {start_date} hingga {end_date}")
        return inventory_report_service.get_inventory_slow_moving_for_export(start_date, end_date)


report_service = ReportService()