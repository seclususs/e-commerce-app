from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.core.db import get_db_connection
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.repository.report_repository import (
    ReportRepository, report_repository
)


class CustomerReportService:

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


    def get_customer_reports(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        
        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            top_spenders = self.report_repository.get_top_spenders(
                conn, start_date, end_date
            )
            return {"top_spenders": top_spenders}
        
        except mysql.connector.Error as db_err:
            raise DatabaseException(
                "Kesalahan database saat membuat laporan pelanggan: "
                f"{db_err}"
            )
        
        except Exception as e:
            raise ServiceLogicError(
                f"Kesalahan layanan saat membuat laporan pelanggan: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def get_cart_analytics(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> Dict[str, Any]:
        
        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            total_carts_created = (
                self.report_repository.get_cart_analytics_created(conn)
            )
            total_orders_completed = (
                self.report_repository.get_cart_analytics_completed(
                    conn, start_date, end_date
                )
            )
            abandonment_rate = (
                (1 - (total_orders_completed / total_carts_created)) * 100
                if total_carts_created > 0
                else 0
            )
            return {
                "abandonment_rate": round(abandonment_rate, 2),
                "carts_created": total_carts_created,
                "orders_completed": total_orders_completed,
            }
        
        except mysql.connector.Error as db_err:
            raise DatabaseException(
                "Kesalahan database saat menghitung analitik keranjang: "
                f"{db_err}"
            )
        
        except Exception as e:
            raise ServiceLogicError(
                f"Kesalahan layanan saat menghitung analitik keranjang: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def get_full_customers_data_for_export(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> List[List[Any]]:
        
        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            data = self.report_repository.get_full_customers_data_for_export(
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
                "Kesalahan database saat mengambil data pelanggan untuk "
                f"ekspor: {db_err}"
            )
        
        except Exception as e:
            raise ServiceLogicError(
                "Kesalahan layanan saat mengambil data pelanggan untuk "
                f"ekspor: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()

customer_report_service = CustomerReportService(report_repository)