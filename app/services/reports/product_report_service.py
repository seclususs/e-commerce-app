from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import mysql.connector
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursorDict

from app.core.db import get_db_connection
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.repository.report_repository import (
    ReportRepository, report_repository
)


class ProductReportService:

    def __init__(self, report_repo: ReportRepository = report_repository):
        self.report_repository = report_repo

        
    def _get_date_filter_clause(
        self,
        start_date: Optional[str],
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


    def get_product_reports(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        
        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            top_selling = self.report_repository.get_top_selling_products(
                conn, start_date, end_date
            )
            most_viewed = self.report_repository.get_most_viewed_products(
                conn
            )
            return {"top_selling": top_selling, "most_viewed": most_viewed}
        
        except mysql.connector.Error as db_err:
            raise DatabaseException(
                f"Kesalahan database saat membuat laporan produk: {db_err}"
            )
        
        except Exception as e:
            raise ServiceLogicError(
                f"Kesalahan layanan saat membuat laporan produk: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def get_top_products_chart_data(
        self, start_date_str: str, end_date_str: str, conn: MySQLConnection
    ) -> Dict[str, List[Any]]:
        
        cursor: Optional[MySQLCursorDict] = None
        try:
            top_products = self.report_repository.get_top_products_chart_data(
                conn, start_date_str, end_date_str
            )
            return {
                "labels": [p["name"] for p in top_products],
                "data": [p["total_sold"] for p in top_products],
            }
        
        except mysql.connector.Error as db_err:
            raise DatabaseException(
                "Kesalahan database saat mengambil data grafik produk "
                f"teratas: {db_err}"
            )
        
        except Exception as e:
            raise ServiceLogicError(
                "Kesalahan layanan saat mengambil data grafik produk "
                f"teratas: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()


    def get_full_products_data_for_export(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> List[List[Any]]:
        
        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            data = self.report_repository.get_full_products_data_for_export(
                conn, start_date, end_date
            )
            processed_data: List[List[Any]] = [
                [
                    float(col) if isinstance(col, Decimal) else col
                    for col in row.values()
                ]
                for row in data
            ]
            return processed_data
        
        except mysql.connector.Error as db_err:
            raise DatabaseException(
                "Kesalahan database saat mengambil data produk untuk "
                f"ekspor: {db_err}"
            )
        
        except Exception as e:
            raise ServiceLogicError(
                "Kesalahan layanan saat mengambil data produk untuk "
                f"ekspor: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()

product_report_service = ProductReportService(report_repository)