from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import mysql.connector
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursorDict

from app.core.db import get_db_connection
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class CustomerReportService:

    def _get_date_filter_clause(
        self,
        start_date: Optional[str],
        end_date: Optional[str],
        table_alias: str = "o",
    ) -> Tuple[str, List[str]]:
        logger.debug(
            f"Membuat klausa filter tanggal. Mulai: {start_date}, "
            f"Selesai: {end_date}, Alias: {table_alias}"
        )

        date_filter = f" WHERE {table_alias}.status != 'Dibatalkan' "

        params: List[str] = []

        if start_date:
            date_filter += f" AND {table_alias}.order_date >= %s "
            params.append(start_date)

        if end_date:
            date_filter += f" AND {table_alias}.order_date <= %s "
            params.append(end_date)
        logger.debug(f"Filter dibuat: {date_filter}, Parameter: {params}")

        return date_filter, params


    def get_customer_reports(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        logger.info(
            f"Membuat laporan pelanggan untuk periode: {start_date} "
            f"hingga {end_date}"
        )

        conn: Optional[MySQLConnection] = None
        cursor: Optional[MySQLCursorDict] = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            date_filter, params = self._get_date_filter_clause(
                start_date, end_date
            )
            query = f"""
                SELECT
                    u.username,
                    u.email,
                    SUM(o.total_amount) AS total_spent
                FROM users u
                JOIN orders o ON u.id = o.user_id
                {date_filter}
                GROUP BY u.id
                ORDER BY total_spent DESC
                LIMIT 10
            """

            logger.debug(
                f"Menjalankan kueri untuk pelanggan teratas: {query} "
                f"with params: {params}"
            )

            cursor.execute(query, tuple(params))
            top_spenders = cursor.fetchall()

            logger.info(f"Mengambil {len(top_spenders)} pelanggan teratas.")

            return {"top_spenders": top_spenders}
        
        except mysql.connector.Error as db_err:
            logger.error(
                "Kesalahan database saat membuat laporan pelanggan: "
                f"{db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                "Kesalahan database saat membuat laporan pelanggan: "
                f"{db_err}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat membuat laporan pelanggan: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat membuat laporan pelanggan: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                "Koneksi database ditutup untuk get_customer_reports."
            )


    def get_cart_analytics(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> Dict[str, Any]:
        logger.info(
            f"Menghitung analitik keranjang untuk periode: {start_date} "
            f"hingga {end_date}"
        )

        conn: Optional[MySQLConnection] = None
        cursor: Optional[MySQLCursorDict] = None
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            date_filter, params = self._get_date_filter_clause(
                start_date, end_date
            )

            cursor.execute(
                "SELECT COUNT(DISTINCT user_id) AS count FROM user_carts"
            )

            total_carts_created = cursor.fetchone()["count"] or 0
            logger.debug(
                "Total keranjang dibuat (pengguna unik): "
                f"{total_carts_created}"
            )

            query_completed = (
                "SELECT COUNT(DISTINCT user_id) AS count FROM orders o "
                f"{date_filter}"
            )
            logger.debug(
                "Menjalankan kueri untuk jumlah pesanan selesai: "
                f"{query_completed} with params: {params}"
            )

            cursor.execute(query_completed, tuple(params))
            total_orders_completed = cursor.fetchone()["count"] or 0

            logger.debug(
                "Total pesanan selesai (pengguna unik): "
                f"{total_orders_completed}"
            )
            abandonment_rate = (
                (1 - (total_orders_completed / total_carts_created)) * 100
                if total_carts_created > 0
                else 0
            )

            logger.info(
                "Tingkat pengabaian keranjang terhitung: "
                f"{abandonment_rate:.2f}%"
            )

            return {
                "abandonment_rate": round(abandonment_rate, 2),
                "carts_created": total_carts_created,
                "orders_completed": total_orders_completed,
            }
        
        except mysql.connector.Error as db_err:
            logger.error(
                "Kesalahan database saat menghitung analitik keranjang: "
                f"{db_err}",
                exc_info=True,
            )

            raise DatabaseException(
                "Kesalahan database saat menghitung analitik keranjang: "
                f"{db_err}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat menghitung analitik keranjang: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat menghitung analitik keranjang: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                "Koneksi database ditutup untuk get_cart_analytics."
            )


    def get_full_customers_data_for_export(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> List[List[Any]]:
        logger.info(
            "Mengambil data pelanggan lengkap untuk ekspor. Periode: "
            f"{start_date} hingga {end_date}"
        )

        conn: Optional[MySQLConnection] = None
        cursor: Optional[MySQLCursorDict] = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            date_filter, params = self._get_date_filter_clause(
                start_date, end_date
            )

            query = f"""
                SELECT
                    u.id,
                    u.username,
                    u.email,
                    SUM(o.total_amount) AS total_spent,
                    COUNT(o.id) AS order_count
                FROM users u
                JOIN orders o ON u.id = o.user_id
                {date_filter}
                GROUP BY u.id
                ORDER BY total_spent DESC
            """

            logger.debug(
                "Menjalankan kueri untuk data ekspor pelanggan: {query} "
                f"with params: {params}"
            )

            cursor.execute(query, tuple(params))
            data = cursor.fetchall()

            logger.info(
                f"Mengambil {len(data)} catatan pelanggan untuk ekspor."
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
            logger.error(
                "Kesalahan database saat mengambil data pelanggan untuk "
                f"ekspor: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                "Kesalahan database saat mengambil data pelanggan untuk "
                f"ekspor: {db_err}"
            )
        
        except Exception as e:
            logger.error(
                "Kesalahan saat mengambil data pelanggan untuk ekspor: "
                f"{e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                "Kesalahan layanan saat mengambil data pelanggan untuk "
                f"ekspor: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                "Koneksi database ditutup untuk "
                "get_full_customers_data_for_export."
            )

customer_report_service = CustomerReportService()