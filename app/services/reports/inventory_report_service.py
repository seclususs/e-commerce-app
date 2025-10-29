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


class InventoryReportService:

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


    def get_inventory_reports(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> Dict[str, Any]:
        
        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            total_value = self.report_repository.get_inventory_total_value(
                conn
            )
            slow_moving = self.report_repository.get_inventory_slow_moving(
                conn, start_date, end_date
            )
            low_stock = self.report_repository.get_inventory_low_stock(conn)
            return {
                "total_value": total_value,
                "slow_moving": slow_moving,
                "low_stock": low_stock,
            }
        
        except mysql.connector.Error as db_err:
            raise DatabaseException(
                "Kesalahan database saat membuat laporan inventaris: "
                f"{db_err}"
            )
        
        except Exception as e:
            raise ServiceLogicError(
                f"Kesalahan layanan saat membuat laporan inventaris: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def get_low_stock_chart_data(
        self, conn: MySQLConnection
    ) -> Dict[str, List[Any]]:
        
        cursor: Optional[MySQLCursorDict] = None
        try:
            low_stock_products = (
                self.report_repository.get_low_stock_chart_data(conn)
            )
            return {
                "labels": [p["name"] for p in low_stock_products],
                "data": [p["stock"] for p in low_stock_products],
            }
        
        except mysql.connector.Error as db_err:
            raise DatabaseException(
                "Kesalahan database saat mengambil data grafik stok rendah: "
                f"{db_err}"
            )
        
        except Exception as e:
            raise ServiceLogicError(
                "Kesalahan layanan saat mengambil data grafik stok rendah: "
                f"{e}"
            )
        
        finally:
            if cursor:
                cursor.close()


    def get_inventory_low_stock_for_export(self) -> List[List[Any]]:
        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            data = self.report_repository.get_inventory_low_stock_for_export(
                conn
            )
            processed_data: List[List[Any]] = [
                [col for col in row.values()] for row in data
            ]
            return processed_data
        
        except mysql.connector.Error as db_err:
            raise DatabaseException(
                "Kesalahan database saat mengambil data stok rendah untuk "
                f"ekspor: {db_err}"
            )
        
        except Exception as e:
            raise ServiceLogicError(
                "Kesalahan layanan saat mengambil data stok rendah untuk "
                f"ekspor: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def get_inventory_slow_moving_for_export(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> List[List[Any]]:
        
        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            data = (
                self.report_repository.get_inventory_slow_moving_for_export(
                    conn, start_date, end_date
                )
            )
            processed_data: List[List[Any]] = [
                [col for col in row.values()] for row in data
            ]
            return processed_data
        
        except mysql.connector.Error as db_err:
            raise DatabaseException(
                "Kesalahan database saat mengambil data produk lambat "
                f"terjual untuk ekspor: {db_err}"
            )
        
        except Exception as e:
            raise ServiceLogicError(
                "Kesalahan layanan saat mengambil data produk lambat "
                f"terjual untuk ekspor: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()

inventory_report_service = InventoryReportService(report_repository)