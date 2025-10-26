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


class ProductReportService:

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

    def get_product_reports(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        logger.info(
            f"Membuat laporan produk untuk periode: {start_date} "
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

            query_top_selling = f"""
                SELECT p.name, SUM(oi.quantity) AS total_sold
                FROM products p
                JOIN order_items oi ON p.id = oi.product_id
                JOIN orders o ON oi.order_id = o.id
                {date_filter}
                GROUP BY p.id
                ORDER BY total_sold DESC
                LIMIT 10
            """

            logger.debug(
                "Menjalankan kueri untuk produk terlaris: "
                f"{query_top_selling} with params: {params}"
            )

            cursor.execute(query_top_selling, tuple(params))
            top_selling = cursor.fetchall()
            logger.info(f"Mengambil {len(top_selling)} produk terlaris.")
            query_most_viewed = """
                SELECT name, popularity
                FROM products
                ORDER BY popularity DESC
                LIMIT 10
            """

            logger.debug(
                "Menjalankan kueri untuk produk paling banyak dilihat: "
                f"{query_most_viewed}"
            )

            cursor.execute(query_most_viewed)
            most_viewed = cursor.fetchall()
            logger.info(
                f"Mengambil {len(most_viewed)} produk paling banyak dilihat."
            )

            return {"top_selling": top_selling, "most_viewed": most_viewed}
        
        except mysql.connector.Error as db_err:
            logger.error(
                f"Kesalahan database saat membuat laporan produk: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat membuat laporan produk: {db_err}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat membuat laporan produk: {e}", exc_info=True
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat membuat laporan produk: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                "Koneksi database ditutup untuk get_product_reports."
            )

    def get_top_products_chart_data(
        self, start_date_str: str, end_date_str: str, conn: MySQLConnection
    ) -> Dict[str, List[Any]]:
        logger.debug(
            f"Mengambil data grafik produk teratas untuk periode: "
            f"{start_date_str} hingga {end_date_str}"
        )

        cursor: Optional[MySQLCursorDict] = None

        try:
            cursor = conn.cursor(dictionary=True)

            query = """
                SELECT p.name, SUM(oi.quantity) AS total_sold
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
                JOIN orders o ON oi.order_id = o.id
                WHERE o.status != 'Dibatalkan'
                AND o.order_date BETWEEN %s AND %s
                GROUP BY p.id
                ORDER BY total_sold DESC
                LIMIT 5
            """

            logger.debug(
                f"Menjalankan kueri untuk grafik produk teratas: {query} "
                f"with params: ({start_date_str}, {end_date_str})"
            )

            cursor.execute(query, (start_date_str, end_date_str))
            top_products = cursor.fetchall()
            logger.info(
                f"Mengambil {len(top_products)} data untuk grafik produk "
                "teratas."
            )
            return {
                "labels": [p["name"] for p in top_products],
                "data": [p["total_sold"] for p in top_products],
            }
        
        except mysql.connector.Error as db_err:
            logger.error(
                "Kesalahan database saat mengambil data grafik produk "
                f"teratas: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                "Kesalahan database saat mengambil data grafik produk "
                f"teratas: {db_err}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat mengambil data grafik produk teratas: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                "Kesalahan layanan saat mengambil data grafik produk "
                f"teratas: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()
            logger.debug(
                "Kursor ditutup untuk get_top_products_chart_data "
                "(koneksi dikelola secara eksternal)."
            )

    def get_full_products_data_for_export(
        self, start_date: Optional[str], end_date: Optional[str]
    ) -> List[List[Any]]:
        logger.info(
            "Mengambil data produk lengkap untuk ekspor. Periode: "
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
            date_filter_for_join = date_filter.replace(
                "WHERE o.status != 'Dibatalkan'", ""
            )

            query = f"""
                SELECT
                    p.id,
                    p.name,
                    c.name AS category_name,
                    p.sku,
                    p.price,
                    p.discount_price,
                    p.stock,
                    (
                        SELECT COALESCE(SUM(oi.quantity), 0)
                        FROM order_items oi
                        JOIN orders o ON oi.order_id = o.id
                        WHERE oi.product_id = p.id
                        AND o.status != 'Dibatalkan'
                        {date_filter_for_join}
                    ) AS total_sold,
                    p.popularity
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                GROUP BY p.id
                ORDER BY total_sold DESC
            """

            logger.debug(
                "Menjalankan kueri untuk data ekspor produk: {query} "
                f"with params: {params}"
            )

            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            logger.info(f"Mengambil {len(data)} data produk untuk ekspor.")

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
                "Kesalahan database saat mengambil data produk untuk "
                f"ekspor: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                "Kesalahan database saat mengambil data produk untuk "
                f"ekspor: {db_err}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat mengambil data produk untuk ekspor: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                "Kesalahan layanan saat mengambil data produk untuk "
                f"ekspor: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                "Koneksi database ditutup untuk "
                "get_full_products_data_for_export."
            )

product_report_service = ProductReportService()