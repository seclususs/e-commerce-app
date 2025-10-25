import mysql.connector
from app.core.db import get_db_connection
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class VariantService:
    

    def get_variants_for_product(self, product_id, conn=None):
        logger.debug(f"Mengambil varian untuk ID produk: {product_id}")
        close_conn = False

        if conn is None:
            conn = get_db_connection()
            close_conn = True
            logger.debug(f"Membuat koneksi DB baru untuk get_variants_for_product {product_id}")

        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(
                "SELECT * FROM product_variants WHERE product_id = %s ORDER BY id",
                (product_id,),
            )
            variants = cursor.fetchall()
            logger.info(f"Mengambil {len(variants)} varian untuk ID produk: {product_id}")
            return variants

        except Exception as e:
            logger.error(f"Kesalahan saat mengambil varian untuk ID produk {product_id}: {e}", exc_info=True)
            raise

        finally:
            cursor.close()
            if close_conn:
                conn.close()
                logger.debug(f"Menutup koneksi DB untuk get_variants_for_product {product_id}")


    def add_variant(self, product_id, size, stock, weight_grams, sku):
        logger.debug(
            f"Mencoba menambahkan varian untuk ID produk: {product_id}. "
            f"Ukuran: {size}, Stok: {stock}, Berat: {weight_grams}, SKU: {sku}"
        )

        try:
            stock_int = int(stock)
            weight_int = int(weight_grams)
            if not size or not stock or stock_int < 0 or not weight_grams or weight_int < 0:
                logger.warning("Penambahan varian gagal: Data input tidak valid.")
                return {'success': False, 'message': 'Ukuran, stok (>=0), dan berat (>=0) harus diisi dengan benar.'}
        except (ValueError, TypeError):
             logger.warning("Penambahan varian gagal: Stok atau berat bukan angka.")
             return {'success': False, 'message': 'Stok dan berat harus berupa angka.'}

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        new_id = None

        try:
            upper_sku = sku.upper().strip() if sku else None
            cursor.execute(
                """
                INSERT INTO product_variants (product_id, size, stock, weight_grams, sku)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (product_id, size.upper().strip(), stock_int, weight_int, upper_sku),
            )
            new_id = cursor.lastrowid
            conn.commit()

            cursor.execute("SELECT * FROM product_variants WHERE id = %s", (new_id,))
            new_variant = cursor.fetchone()
            logger.info(
                f"Varian '{size.upper()}' berhasil ditambahkan untuk ID produk {product_id}. "
                f"ID varian baru: {new_id}"
            )

            self.update_total_stock_from_variants(product_id, conn)

            return {
                'success': True,
                'message': f'Varian {size.upper()} berhasil ditambahkan.',
                'data': new_variant,
            }

        except mysql.connector.IntegrityError as e:
            conn.rollback()
            if e.errno == 1062:
                field = 'SKU' if 'sku' in str(e).lower() else 'ukuran'
                value = upper_sku if field == 'SKU' else size.upper()
                logger.warning(f"Penambahan varian gagal: {field} duplikat '{value}' untuk ID produk {product_id}.")
                return {'success': False, 'message': f'{field} "{value}" sudah ada untuk produk ini. Harap gunakan yang unik.'}

            logger.error(f"Kesalahan integritas database saat menambahkan varian untuk ID produk {product_id}: {e}", exc_info=True)
            return {'success': False, 'message': 'Terjadi kesalahan database (Integrity).'}

        except Exception as e:
            conn.rollback()
            logger.error(f"Kesalahan tak terduga saat menambahkan varian untuk ID produk {product_id}: {e}", exc_info=True)
            return {'success': False, 'message': 'Gagal menambahkan varian.'}

        finally:
            cursor.close()
            conn.close()
            logger.debug(f"Koneksi database ditutup untuk add_variant {product_id}")


    def update_variant(self, product_id, variant_id, size, stock, weight_grams, sku):
        logger.debug(
            f"Mencoba memperbarui ID varian: {variant_id} (Produk ID: {product_id}). "
            f"Ukuran: {size}, Stok: {stock}, Berat: {weight_grams}, SKU: {sku}"
        )

        try:
            stock_int = int(stock)
            weight_int = int(weight_grams)
            if not size or not stock or stock_int < 0 or not weight_grams or weight_int < 0:
                logger.warning(f"Pembaruan varian gagal untuk ID {variant_id}: Data input tidak valid.")
                return {'success': False, 'message': 'Ukuran, stok (>=0), dan berat (>=0) harus diisi dengan benar.'}
        except (ValueError, TypeError):
             logger.warning(f"Pembaruan varian gagal untuk ID {variant_id}: Stok atau berat bukan angka.")
             return {'success': False, 'message': 'Stok dan berat harus berupa angka.'}

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            upper_sku = sku.upper().strip() if sku else None
            cursor.execute(
                """
                UPDATE product_variants
                SET size = %s, stock = %s, weight_grams = %s, sku = %s
                WHERE id = %s AND product_id = %s
                """,
                (size.upper().strip(), stock_int, weight_int, upper_sku, variant_id, product_id),
            )

            if cursor.rowcount > 0:
                conn.commit()
                self.update_total_stock_from_variants(product_id, conn)
                logger.info(f"ID Varian {variant_id} berhasil diperbarui.")
                return {'success': True, 'message': 'Varian berhasil diperbarui.'}

            conn.rollback()
            logger.warning(f"Pembaruan varian gagal: ID Varian {variant_id} tidak ditemukan untuk produk ID {product_id}.")
            return {'success': False, 'message': 'Varian tidak ditemukan atau tidak sesuai.'}

        except mysql.connector.IntegrityError as e:
            conn.rollback()
            if e.errno == 1062:
                field = 'SKU' if 'sku' in str(e).lower() else 'ukuran'
                value = upper_sku if field == 'SKU' else size.upper()
                logger.warning(f"Pembaruan varian gagal untuk ID {variant_id}: {field} duplikat '{value}'.")
                return {'success': False, 'message': f'{field} "{value}" sudah ada untuk produk ini. Harap gunakan yang unik.'}

            logger.error(f"Kesalahan integritas database saat memperbarui ID varian {variant_id}: {e}", exc_info=True)
            return {'success': False, 'message': 'Terjadi kesalahan database (Integrity).'}

        except Exception as e:
            conn.rollback()
            logger.error(f"Kesalahan tak terduga saat memperbarui ID varian {variant_id}: {e}", exc_info=True)
            return {'success': False, 'message': 'Gagal memperbarui varian.'}

        finally:
            cursor.close()
            conn.close()
            logger.debug(f"Koneksi database ditutup untuk update_variant {variant_id}")


    def delete_variant(self, product_id, variant_id):
        logger.debug(f"Mencoba menghapus ID varian: {variant_id} dari produk ID: {product_id}")
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM product_variants WHERE id = %s AND product_id = %s", (variant_id, product_id))

            if cursor.rowcount > 0:
                conn.commit()
                self.update_total_stock_from_variants(product_id, conn)
                logger.info(f"ID Varian {variant_id} berhasil dihapus.")
                return {'success': True, 'message': 'Varian berhasil dihapus.'}

            conn.rollback()
            logger.warning(f"Penghapusan varian gagal: ID Varian {variant_id} tidak ditemukan untuk produk ID {product_id}.")
            return {'success': False, 'message': 'Varian tidak ditemukan atau tidak sesuai.'}

        except Exception as e:
            conn.rollback()
            logger.error(f"Kesalahan saat menghapus ID varian {variant_id}: {e}", exc_info=True)
            return {'success': False, 'message': 'Gagal menghapus varian.'}

        finally:
            cursor.close()
            conn.close()
            logger.debug(f"Koneksi database ditutup untuk delete_variant {variant_id}")


    def delete_all_variants_for_product(self, product_id, conn):
        logger.debug(f"Menghapus semua varian untuk ID produk: {product_id}")
        cursor = conn.cursor()
        is_external_conn = conn is not None

        try:
            cursor.execute("DELETE FROM product_variants WHERE product_id = %s", (product_id,))
            deleted_count = cursor.rowcount
            if not is_external_conn:
                conn.commit()
            logger.info(f"Menghapus {deleted_count} varian untuk ID produk {product_id}.")

        except Exception as e:
            logger.error(f"Kesalahan saat menghapus semua varian untuk ID produk {product_id}: {e}", exc_info=True)
            if not is_external_conn:
                conn.rollback()
            raise

        finally:
            cursor.close()
            if not is_external_conn:
                conn.close()
                logger.debug(f"Koneksi DB ditutup untuk delete_all_variants_for_product {product_id}")


    def update_total_stock_from_variants(self, product_id, conn=None):
        logger.debug(f"Memperbarui total stok dari varian untuk ID produk: {product_id}")
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
            logger.debug("Membuat koneksi DB baru untuk update_total_stock_from_variants.")

        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(
                "SELECT SUM(stock) AS total FROM product_variants WHERE product_id = %s",
                (product_id,),
            )
            total_stock_row = cursor.fetchone()
            total_stock = total_stock_row['total'] if total_stock_row and total_stock_row['total'] is not None else 0

            cursor.execute("UPDATE products SET stock = %s WHERE id = %s", (total_stock, product_id))


            if close_conn:
                conn.commit()

            logger.info(f"Memperbarui total stok untuk ID produk {product_id} menjadi {total_stock}.")
            return True

        except Exception as e:
            logger.error(f"Kesalahan saat memperbarui total stok untuk ID produk {product_id}: {e}", exc_info=True)
            if close_conn and conn.is_connected():
                conn.rollback()
            return False

        finally:
            cursor.close()
            if close_conn:
                conn.close()
                logger.debug(f"Koneksi database ditutup untuk update_total_stock_from_variants {product_id}")


variant_service = VariantService()