from decimal import Decimal
from typing import Any, Dict, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.core.db import get_db_connection
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.repository.report_repository import (
    ReportRepository, report_repository
)

from .inventory_report_service import inventory_report_service
from .product_report_service import product_report_service
from .sales_report_service import sales_report_service


def convert_decimals(obj: Any) -> Any:
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj


class DashboardReportService:

    def __init__(self, report_repo: ReportRepository = report_repository):
        self.report_repository = report_repo


    def get_dashboard_stats(
        self, start_date_str: str, end_date_str: str
    ) -> Dict[str, Any]:
        
        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            total_sales = self.report_repository.get_dashboard_sales(
                conn, start_date_str, end_date_str
            )
            order_count = self.report_repository.get_dashboard_order_count(
                conn, start_date_str, end_date_str
            )
            new_user_count = (
                self.report_repository.get_dashboard_new_user_count(
                    conn, start_date_str, end_date_str
                )
            )
            product_count = (
                self.report_repository.get_dashboard_product_count(conn)
            )
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
            stats = {
                "total_sales": total_sales,
                "order_count": order_count,
                "new_user_count": new_user_count,
                "product_count": product_count,
                "sales_chart_data": sales_chart_data,
                "top_products_chart": top_products_chart,
                "low_stock_chart": low_stock_chart,
            }
            return stats
        
        except mysql.connector.Error as db_err:
            raise DatabaseException(
                "Kesalahan database saat mengambil statistik dasbor: "
                f"{db_err}"
            )
        
        except Exception as e:
            raise ServiceLogicError(
                f"Kesalahan layanan saat mengambil statistik dasbor: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()

dashboard_report_service = DashboardReportService(report_repository)