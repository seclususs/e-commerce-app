import decimal
from app.core.db import get_db_connection
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class InventoryReportService:


    def _get_date_filter_clause(self, start_date, end_date, table_alias='o'):
        logger.debug(
            f"Membuat klausa filter tanggal. Mulai: {start_date}, Selesai: {end_date}, Alias: {table_alias}"
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


    def get_inventory_reports(self, start_date, end_date):
        logger.info(f"Membuat laporan inventaris untuk periode: {start_date} hingga {end_date}")

        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            query_total_value = """
                SELECT SUM(total_value) AS total_value
                FROM (
                    SELECT 
                        (CASE 
                            WHEN p.discount_price IS NOT NULL AND p.discount_price > 0 
                            THEN p.discount_price 
                            ELSE p.price 
                        END) * p.stock AS total_value 
                    FROM products p 
                    WHERE p.has_variants = 0

                    UNION ALL

                    SELECT 
                        (CASE 
                            WHEN p.discount_price IS NOT NULL AND p.discount_price > 0 
                            THEN p.discount_price 
                            ELSE p.price 
                        END) * pv.stock AS total_value 
                    FROM product_variants pv 
                    JOIN products p ON pv.product_id = p.id
                ) AS inventory_values
            """

            logger.debug(f"Menjalankan kueri untuk total nilai inventaris: {query_total_value}")
            cursor.execute(query_total_value)
            total_value = cursor.fetchone()['total_value'] or 0
            logger.debug(f"Menghitung total nilai inventaris: {total_value}")

            date_filter_orders, params_orders = self._get_date_filter_clause(start_date, end_date, 'o')
            date_filter_for_join = date_filter_orders.replace("WHERE o.status != 'Dibatalkan'", "")

            query_slow_moving = f"""
                SELECT 
                    p.name, 
                    p.stock,
                    (
                        SELECT COALESCE(SUM(oi.quantity), 0) 
                        FROM order_items oi 
                        JOIN orders o ON oi.order_id = o.id 
                        WHERE oi.product_id = p.id 
                        AND o.status != 'Dibatalkan' 
                        {date_filter_for_join}
                    ) AS total_sold
                FROM products p 
                GROUP BY p.id 
                ORDER BY total_sold ASC, p.stock DESC 
                LIMIT 10
            """

            logger.debug(f"Menjalankan kueri untuk produk yang lambat terjual: {query_slow_moving} dengan params: {params_orders}")
            cursor.execute(query_slow_moving, tuple(params_orders))
            slow_moving = cursor.fetchall()
            logger.info(f"Mengambil {len(slow_moving)} produk yang lambat terjual.")

            query_low_stock = """
                SELECT 
                    name, 
                    stock, 
                    'Produk Utama' AS type, 
                    id AS product_id, 
                    NULL AS variant_id
                FROM products 
                WHERE has_variants = 0 
                AND stock <= 5 
                AND stock > 0

                UNION ALL

                SELECT 
                    CONCAT(p.name, ' (', pv.size, ')') AS name, 
                    pv.stock, 
                    'Varian' AS type, 
                    p.id AS product_id, 
                    pv.id AS variant_id
                FROM product_variants pv 
                JOIN products p ON pv.product_id = p.id 
                WHERE pv.stock <= 5 
                AND pv.stock > 0

                ORDER BY stock ASC
            """

            logger.debug(f"Menjalankan kueri untuk produk stok rendah: {query_low_stock}")
            cursor.execute(query_low_stock)
            low_stock = cursor.fetchall()
            logger.info(f"Mengambil {len(low_stock)} produk/varian stok rendah.")

            return {
                'total_value': total_value,
                'slow_moving': slow_moving,
                'low_stock': low_stock,
            }

        except Exception as e:
            logger.error(f"Kesalahan saat membuat laporan inventaris: {e}", exc_info=True)
            raise

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug("Koneksi database ditutup untuk get_inventory_reports.")


    def get_low_stock_chart_data(self, conn):
        logger.debug("Mengambil data grafik stok rendah.")
        cursor = None

        try:
            cursor = conn.cursor(dictionary=True)

            low_stock_products_query = """
                SELECT 
                    name, 
                    stock, 
                    id AS product_id 
                FROM products 
                WHERE has_variants = 0 
                AND stock <= 5 
                AND stock > 0

                UNION ALL

                SELECT 
                    CONCAT(p.name, ' (', pv.size, ')') AS name, 
                    pv.stock, 
                    p.id AS product_id 
                FROM product_variants pv 
                JOIN products p ON pv.product_id = p.id 
                WHERE pv.stock <= 5 
                AND pv.stock > 0

                ORDER BY stock ASC 
                LIMIT 7
            """

            logger.debug(f"Menjalankan kueri untuk data grafik stok rendah: {low_stock_products_query}")
            cursor.execute(low_stock_products_query)
            low_stock_products = cursor.fetchall()
            logger.info(f"Mengambil {len(low_stock_products)} data untuk grafik stok rendah.")

            return {
                'labels': [p['name'] for p in low_stock_products],
                'data': [p['stock'] for p in low_stock_products],
            }

        except Exception as e:
            logger.error(f"Kesalahan saat mengambil data grafik stok rendah: {e}", exc_info=True)
            raise

        finally:
            if cursor:
                cursor.close()
            logger.debug("Kursor ditutup untuk get_low_stock_chart_data (koneksi dikelola secara eksternal).")


    def get_inventory_low_stock_for_export(self):
        logger.info("Mengambil data inventaris stok rendah untuk ekspor.")

        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            query = """
                SELECT 
                    name, 
                    stock, 
                    'Produk Utama' AS type, 
                    id AS product_id, 
                    NULL AS variant_id, 
                    sku
                FROM products 
                WHERE has_variants = 0 
                AND stock <= 5 
                AND stock > 0

                UNION ALL

                SELECT 
                    CONCAT(p.name, ' (', pv.size, ')') AS name, 
                    pv.stock, 
                    'Varian' AS type, 
                    p.id AS product_id, 
                    pv.id AS variant_id, 
                    pv.sku
                FROM product_variants pv 
                JOIN products p ON pv.product_id = p.id 
                WHERE pv.stock <= 5 
                AND pv.stock > 0

                ORDER BY stock ASC
            """

            logger.debug(f"Menjalankan kueri untuk ekspor stok rendah: {query}")
            cursor.execute(query)
            data = cursor.fetchall()
            logger.info(f"Mengambil {len(data)} data stok rendah untuk ekspor.")

            processed_data = [[col for col in row.values()] for row in data]
            return processed_data

        except Exception as e:
            logger.error(f"Kesalahan saat mengambil data stok rendah untuk ekspor: {e}", exc_info=True)
            raise

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug("Koneksi database ditutup untuk get_inventory_low_stock_for_export.")


    def get_inventory_slow_moving_for_export(self, start_date, end_date):
        logger.info(f"Mengambil data inventaris yang lambat terjual untuk ekspor. Periode: {start_date} hingga {end_date}")

        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            date_filter, params = self._get_date_filter_clause(start_date, end_date)
            date_filter_for_join = date_filter.replace("WHERE o.status != 'Dibatalkan'", "")

            query = f"""
                SELECT 
                    p.name, 
                    p.stock,
                    (
                        SELECT COALESCE(SUM(oi.quantity), 0) 
                        FROM order_items oi 
                        JOIN orders o ON oi.order_id = o.id 
                        WHERE oi.product_id = p.id 
                        AND o.status != 'Dibatalkan' 
                        {date_filter_for_join}
                    ) AS total_sold
                FROM products p 
                GROUP BY p.id 
                ORDER BY total_sold ASC, p.stock DESC 
                LIMIT 20
            """

            logger.debug(f"Menjalankan kueri untuk ekspor produk lambat terjual: {query} with params: {params}")
            cursor.execute(query, tuple(params))
            data = cursor.fetchall()
            logger.info(f"Mengambil {len(data)} data produk lambat terjual untuk ekspor.")

            processed_data = [[col for col in row.values()] for row in data]
            return processed_data

        except Exception as e:
            logger.error(f"Kesalahan saat mengambil data produk lambat terjual untuk ekspor: {e}", exc_info=True)
            raise

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug("Koneksi database ditutup untuk get_inventory_slow_moving_for_export.")


inventory_report_service = InventoryReportService()