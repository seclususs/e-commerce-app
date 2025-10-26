from decimal import Decimal
from typing import Any, Dict, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursorDict

from app.core.db import get_db_connection
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.utils.logging_utils import get_logger

from .inventory_report_service import inventory_report_service
from .product_report_service import product_report_service
from .sales_report_service import sales_report_service

logger = get_logger(__name__)


def convert_decimals(obj: Any) -> Any:
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj


class DashboardReportService:

    def get_dashboard_stats(
        self, start_date_str: str, end_date_str: str
    ) -> Dict[str, Any]:
        logger.info(
            "Mengambil statistik dasbor untuk periode: "
            f"{start_date_str} hingga {end_date_str}"
        )

        conn: Optional[MySQLConnection] = None
        cursor: Optional[MySQLCursorDict] = None
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
            total_sales = cursor.fetchone()["total"] or 0
            logger.debug(f"Total penjualan dihitung: {total_sales}")

            query_orders = """
                SELECT COUNT(id) AS count
                FROM orders
                WHERE order_date BETWEEN %s AND %s
            """

            cursor.execute(query_orders, (start_date_str, end_date_str))
            order_count = cursor.fetchone()["count"] or 0
            logger.debug(f"Jumlah pesanan dihitung: {order_count}")

            query_users = """
                SELECT COUNT(id) AS count
                FROM users
                WHERE created_at BETWEEN %s AND %s
            """

            cursor.execute(query_users, (start_date_str, end_date_str))
            new_user_count = cursor.fetchone()["count"] or 0

            logger.debug(f"Jumlah pengguna baru dihitung: {new_user_count}")

            query_products = "SELECT COUNT(id) AS count FROM products"

            cursor.execute(query_products)
            product_count = cursor.fetchone()["count"] or 0
            logger.debug(f"Jumlah total produk dihitung: {product_count}")

            logger.debug("Mengambil data grafik...")
            sales_chart_data = sales_report_service.get_sales_chart_data(
                start_date_str, end_date_str, conn
            )
            top_products_chart = (
                product_report_service.get_top_products_chart_data(
                    start_date_str, end_date_str, conn
                )
            )
            low_stock_chart = (
                inventory_report_service.get_low_stock_chart_data(conn)
            )
            logger.debug("Data grafik diambil.")

            stats = {
                "total_sales": total_sales,
                "order_count": order_count,
                "new_user_count": new_user_count,
                "product_count": product_count,
                "sales_chart_data": sales_chart_data,
                "top_products_chart": top_products_chart,
                "low_stock_chart": low_stock_chart,
            }
            logger.info("Pengambilan statistik dasbor selesai.")

            return stats
        
        except mysql.connector.Error as db_err:
            logger.error(
                "Kesalahan database saat mengambil statistik dasbor: "
                f"{db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                "Kesalahan database saat mengambil statistik dasbor: "
                f"{db_err}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat mengambil statistik dasbor: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat mengambil statistik dasbor: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                "Koneksi database ditutup untuk get_dashboard_stats."
            )

dashboard_report_service = DashboardReportService()