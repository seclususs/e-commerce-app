from datetime import datetime, timedelta
import decimal
from app.core.db import get_db_connection
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class SalesReportService:


    def _get_date_filter_clause(self, start_date, end_date, table_alias='o'):
        logger.debug(
            f"Membuat klausa filter tanggal. Mulai: {start_date}, "
            f"Selesai: {end_date}, Alias: {table_alias}"
        )

        date_filter = f" WHERE {table_alias}.status != 'Dibatalkan' "
        params = []

        if start_date:
            date_filter += f" AND {table_alias}.order_date >= %s "
            params.append(start_date)
        if end_date:
            date_filter += f" AND {table_alias}.order_date <= %s "
            params.append(end_date)

        logger.debug(f"Filter dibuat: {date_filter}, Parameter: {params}")
        return date_filter, params


    def get_sales_summary(self, start_date, end_date):
        logger.info(f"Membuat ringkasan penjualan untuk periode: {start_date} hingga {end_date}")
        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            date_filter, params = self._get_date_filter_clause(start_date, end_date)

            query = f"""
                SELECT
                    COALESCE(SUM(o.total_amount), 0) AS total_revenue,
                    COUNT(o.id) AS total_orders,
                    COALESCE(SUM(oi.quantity), 0) AS total_items_sold
                FROM orders o
                LEFT JOIN order_items oi ON o.id = oi.order_id
                {date_filter}
            """

            logger.debug(f"Menjalankan kueri untuk ringkasan penjualan: {query} with params: {params}")
            cursor.execute(query, tuple(params))
            report = cursor.fetchone()

            logger.info(
                f"Ringkasan penjualan dibuat: Pendapatan={report['total_revenue']}, "
                f"Pesanan={report['total_orders']}, Item={report['total_items_sold']}"
            )
            return report

        except Exception as e:
            logger.error(f"Kesalahan saat membuat ringkasan penjualan: {e}", exc_info=True)
            raise

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug("Koneksi database ditutup untuk get_sales_summary.")


    def get_voucher_effectiveness(self, start_date, end_date):
        logger.info(f"Membuat laporan efektivitas voucher untuk periode: {start_date} hingga {end_date}")
        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            date_filter, params = self._get_date_filter_clause(start_date, end_date)
            date_filter_and = date_filter.replace('WHERE', 'AND')

            query = f"""
                SELECT
                    voucher_code,
                    COUNT(id) AS usage_count,
                    SUM(discount_amount) AS total_discount
                FROM orders o
                WHERE voucher_code IS NOT NULL {date_filter_and}
                GROUP BY voucher_code
                ORDER BY usage_count DESC;
            """

            logger.debug(f"Menjalankan kueri untuk efektivitas voucher: {query} with params: {params}")
            cursor.execute(query, tuple(params))
            report = cursor.fetchall()

            logger.info(f"Mengambil {len(report)} data untuk efektivitas voucher.")
            return report

        except Exception as e:
            logger.error(f"Kesalahan saat membuat laporan efektivitas voucher: {e}", exc_info=True)
            raise

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug("Koneksi database ditutup untuk get_voucher_effectiveness.")


    def get_sales_chart_data(self, start_date_str, end_date_str, conn):
        logger.debug(f"Mengambil data grafik penjualan untuk periode: {start_date_str} hingga {end_date_str}")
        cursor = None

        try:
            cursor = conn.cursor(dictionary=True)

            query = """
                SELECT
                    DATE(order_date) AS sale_date,
                    SUM(total_amount) AS daily_total
                FROM orders
                WHERE status != 'Dibatalkan' AND order_date BETWEEN %s AND %s
                GROUP BY sale_date
                ORDER BY sale_date ASC
            """

            logger.debug(f"Menjalankan kueri untuk data grafik penjualan with params: ({start_date_str}, {end_date_str})")
            cursor.execute(query, (start_date_str, end_date_str))
            sales_data_raw = cursor.fetchall()

            logger.debug(f"Mengambil {len(sales_data_raw)} poin data mentah untuk grafik penjualan.")

            sales_by_date = {
                row['sale_date'].strftime('%Y-%m-%d'): row['daily_total']
                for row in sales_data_raw
            }

            labels, data = [], []
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d %H:%M:%S').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S').date()
            delta = end_date - start_date

            for i in range(delta.days + 1):
                current_date = start_date + timedelta(days=i)
                date_str = current_date.strftime('%Y-%m-%d')
                labels.append(current_date.strftime('%d %b'))
                data.append(float(sales_by_date.get(date_str, 0)))

            logger.info(f"Memproses data grafik penjualan dengan {len(labels)} label.")
            return {'labels': labels, 'data': data}

        except Exception as e:
            logger.error(f"Kesalahan saat mengambil data grafik penjualan: {e}", exc_info=True)
            raise

        finally:
            if cursor:
                cursor.close()
            logger.debug("Kursor ditutup untuk get_sales_chart_data (koneksi dikelola secara eksternal).")


    def get_full_sales_data_for_export(self, start_date, end_date):
        logger.info(f"Mengambil data penjualan lengkap untuk ekspor. Periode: {start_date} hingga {end_date}")
        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            date_filter, params = self._get_date_filter_clause(start_date, end_date)

            query = f"""
                SELECT
                    o.id,
                    o.order_date,
                    o.shipping_name,
                    u.email,
                    o.subtotal,
                    o.discount_amount,
                    o.shipping_cost,
                    o.total_amount,
                    o.status,
                    o.payment_method,
                    o.voucher_code
                FROM orders o
                LEFT JOIN users u ON o.user_id = u.id
                {date_filter}
                ORDER BY o.order_date DESC
            """

            logger.debug(f"Menjalankan kueri untuk data ekspor penjualan: {query} with params: {params}")
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()

            logger.info(f"Mengambil {len(data)} data penjualan untuk ekspor.")

            processed_data = [
                [float(col) if isinstance(col, decimal.Decimal) else col for col in row.values()]
                for row in data
            ]
            return processed_data

        except Exception as e:
            logger.error(f"Kesalahan saat mengambil data penjualan untuk ekspor: {e}", exc_info=True)
            raise

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug("Koneksi database ditutup untuk get_full_sales_data_for_export.")


    def get_full_vouchers_data_for_export(self, start_date, end_date):
        logger.info(f"Mengambil data voucher lengkap untuk ekspor. Periode: {start_date} hingga {end_date}")
        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            date_filter, params = self._get_date_filter_clause(start_date, end_date)
            date_filter_voucher = date_filter.replace("WHERE o.status != 'Dibatalkan'", "")

            query = f"""
                SELECT
                    v.code,
                    v.type,
                    v.value,
                    (
                        SELECT COUNT(o.id)
                        FROM orders o
                        WHERE o.voucher_code = v.code AND o.status != 'Dibatalkan' {date_filter_voucher}
                    ) AS usage_count,
                    (
                        SELECT COALESCE(SUM(o.discount_amount), 0)
                        FROM orders o
                        WHERE o.voucher_code = v.code AND o.status != 'Dibatalkan' {date_filter_voucher}
                    ) AS total_discount
                FROM vouchers v
                ORDER BY usage_count DESC
            """

            logger.debug(f"Menjalankan kueri untuk data ekspor voucher: {query} with params: {params * 2}")
            cursor.execute(query, tuple(params * 2))
            data = cursor.fetchall()

            logger.info(f"Mengambil {len(data)} data voucher untuk ekspor.")

            processed_data = [
                [float(col) if isinstance(col, decimal.Decimal) else col for col in row.values()]
                for row in data
            ]
            return processed_data

        except Exception as e:
            logger.error(f"Kesalahan saat mengambil data voucher untuk ekspor: {e}", exc_info=True)
            raise

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug("Koneksi database ditutup untuk get_full_vouchers_data_for_export.")


sales_report_service = SalesReportService()