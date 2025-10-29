from datetime import datetime, timedelta
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


class SalesReportService:

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


    def get_sales_summary(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> Dict[str, Any]:
        
        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            report = self.report_repository.get_sales_summary(
                conn, start_date, end_date
            )
            return report or {
                "total_revenue": 0,
                "total_orders": 0,
                "total_items_sold": 0,
            }
        
        except mysql.connector.Error as db_err:
            raise DatabaseException(
                "Kesalahan database saat membuat ringkasan penjualan: "
                f"{db_err}"
            )
        
        except Exception as e:
            raise ServiceLogicError(
                f"Kesalahan layanan saat membuat ringkasan penjualan: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def get_voucher_effectiveness(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> List[Dict[str, Any]]:
        
        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            report = self.report_repository.get_voucher_effectiveness(
                conn, start_date, end_date
            )
            return report
        
        except mysql.connector.Error as db_err:
            raise DatabaseException(
                "Kesalahan database saat membuat laporan efektivitas "
                f"voucher: {db_err}"
            )
        
        except Exception as e:
            raise ServiceLogicError(
                "Kesalahan layanan saat membuat laporan efektivitas "
                f"voucher: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def get_sales_chart_data(
        self, start_date_str: str, end_date_str: str, conn: MySQLConnection
    ) -> Dict[str, List[Any]]:
        
        cursor: Optional[MySQLCursorDict] = None
        try:
            sales_data_raw = self.report_repository.get_sales_chart_data(
                conn, start_date_str, end_date_str
            )
            sales_by_date = {
                row["sale_date"].strftime("%Y-%m-%d"): row["daily_total"]
                for row in sales_data_raw
            }
            labels: List[str] = []
            data: List[float] = []
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S").date()
            delta = end_date - start_date
            for i in range(delta.days + 1):
                current_date = start_date + timedelta(days=i)
                date_str = current_date.strftime("%Y-%m-%d")
                labels.append(current_date.strftime("%d %b"))
                data.append(float(sales_by_date.get(date_str, 0)))
            return {"labels": labels, "data": data}
        
        except mysql.connector.Error as db_err:
            raise DatabaseException(
                "Kesalahan database saat mengambil data grafik penjualan: "
                f"{db_err}"
            )
        
        except Exception as e:
            raise ServiceLogicError(
                f"Kesalahan layanan saat mengambil data grafik penjualan: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()


    def get_full_sales_data_for_export(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> List[List[Any]]:
        
        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            data = self.report_repository.get_full_sales_data_for_export(
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
                "Kesalahan database saat mengambil data penjualan untuk "
                f"ekspor: {db_err}"
            )
        
        except Exception as e:
            raise ServiceLogicError(
                "Kesalahan layanan saat mengambil data penjualan untuk "
                f"ekspor: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def get_full_vouchers_data_for_export(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> List[List[Any]]:
        
        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            data = self.report_repository.get_full_vouchers_data_for_export(
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
                "Kesalahan database saat mengambil data voucher untuk "
                f"ekspor: {db_err}"
            )
        
        except Exception as e:
            raise ServiceLogicError(
                "Kesalahan layanan saat mengambil data voucher untuk "
                f"ekspor: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()

sales_report_service = SalesReportService(report_repository)