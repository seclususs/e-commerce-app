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

        if not size or not stock or int(stock) < 0 or not weight_grams or int(weight_grams) < 0:
            logger.warning("Penambahan varian gagal: Data input tidak valid.")
            return {'success': False, 'message': 'Ukuran, stok, dan berat harus diisi dengan benar.'}

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            upper_sku = sku.upper() if sku else None
            cursor.execute(
                """
                INSERT INTO product_variants (product_id, size, stock, weight_grams, sku)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (product_id, size.upper(), stock, weight_grams, upper_sku),
            )
            new_id = cursor.lastrowid
            conn.commit()

            cursor.execute("SELECT * FROM product_variants WHERE id = %s", (new_id,))
            new_variant = cursor.fetchone()
            logger.info(
                f"Varian '{size.upper()}' berhasil ditambahkan untuk ID produk {product_id}. "
                f"ID varian baru: {new_id}"
            )
            return {
                'success': True,
                'message': f'Varian {size.upper()} berhasil ditambahkan.',
                'data': new_variant,
            }

        except mysql.connector.IntegrityError as e:
            conn.rollback()
            if e.errno == 1062:
                logger.warning(f"Penambahan varian gagal: SKU duplikat '{upper_sku}' untuk ID produk {product_id}.")
                return {'success': False, 'message': f'SKU "{upper_sku}" sudah ada. Harap gunakan SKU yang unik.'}

            logger.error(f"Kesalahan integritas database saat menambahkan varian untuk ID produk {product_id}: {e}", exc_info=True)
            return {'success': False, 'message': 'Terjadi kesalahan database.'}

        except Exception as e:
            conn.rollback()
            logger.error(f"Kesalahan tak terduga saat menambahkan varian untuk ID produk {product_id}: {e}", exc_info=True)
            return {'success': False, 'message': 'Gagal menambahkan varian.'}

        finally:
            cursor.close()
            conn.close()
            logger.debug(f"Koneksi database ditutup untuk add_variant {product_id}")

    def update_variant(self, variant_id, size, stock, weight_grams, sku):
        logger.debug(
            f"Mencoba memperbarui ID varian: {variant_id}. "
            f"Ukuran: {size}, Stok: {stock}, Berat: {weight_grams}, SKU: {sku}"
        )

        if not size or not stock or int(stock) < 0 or not weight_grams or int(weight_grams) < 0:
            logger.warning(f"Pembaruan varian gagal untuk ID {variant_id}: Data input tidak valid.")
            return {'success': False, 'message': 'Ukuran, stok, dan berat harus diisi dengan benar.'}

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            upper_sku = sku.upper() if sku else None
            cursor.execute(
                """
                UPDATE product_variants
                SET size = %s, stock = %s, weight_grams = %s, sku = %s
                WHERE id = %s
                """,
                (size.upper(), stock, weight_grams, upper_sku, variant_id),
            )
            conn.commit()

            if cursor.rowcount > 0:
                logger.info(f"ID Varian {variant_id} berhasil diperbarui.")
                return {'success': True, 'message': 'Varian berhasil diperbarui.'}

            logger.warning(f"Pembaruan varian gagal: ID Varian {variant_id} tidak ditemukan.")
            return {'success': False, 'message': 'Varian tidak ditemukan.'}

        except mysql.connector.IntegrityError as e:
            conn.rollback()
            if e.errno == 1062:
                logger.warning(f"Pembaruan varian gagal untuk ID {variant_id}: SKU duplikat '{upper_sku}'.")
                return {'success': False, 'message': f'SKU "{upper_sku}" sudah ada. Harap gunakan SKU yang unik.'}

            logger.error(f"Kesalahan integritas database saat memperbarui ID varian {variant_id}: {e}", exc_info=True)
            return {'success': False, 'message': 'Terjadi kesalahan database.'}

        except Exception as e:
            conn.rollback()
            logger.error(f"Kesalahan tak terduga saat memperbarui ID varian {variant_id}: {e}", exc_info=True)
            return {'success': False, 'message': 'Gagal memperbarui varian.'}

        finally:
            cursor.close()
            conn.close()
            logger.debug(f"Koneksi database ditutup untuk update_variant {variant_id}")

    def delete_variant(self, variant_id):
        logger.debug(f"Mencoba menghapus ID varian: {variant_id}")
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM product_variants WHERE id = %s", (variant_id,))
            conn.commit()

            if cursor.rowcount > 0:
                logger.info(f"ID Varian {variant_id} berhasil dihapus.")
                return {'success': True, 'message': 'Varian berhasil dihapus.'}

            logger.warning(f"Penghapusan varian gagal: ID Varian {variant_id} tidak ditemukan.")
            return {'success': False, 'message': 'Varian tidak ditemukan.'}

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

        try:
            cursor.execute("DELETE FROM product_variants WHERE product_id = %s", (product_id,))
            logger.info(f"Menghapus {cursor.rowcount} varian untuk ID produk {product_id}.")

        except Exception as e:
            logger.error(f"Kesalahan saat menghapus semua varian untuk ID produk {product_id}: {e}", exc_info=True)
            raise

        finally:
            cursor.close()

    def update_total_stock_from_variants(self, product_id):
        logger.debug(f"Memperbarui total stok dari varian untuk ID produk: {product_id}")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(
                "SELECT SUM(stock) AS total FROM product_variants WHERE product_id = %s",
                (product_id,),
            )
            total_stock_row = cursor.fetchone()
            total_stock = total_stock_row['total'] if total_stock_row and total_stock_row['total'] is not None else 0

            cursor.execute("UPDATE products SET stock = %s WHERE id = %s", (total_stock, product_id))
            conn.commit()
            logger.info(f"Memperbarui total stok untuk ID produk {product_id} menjadi {total_stock}.")

        except Exception as e:
            conn.rollback()
            logger.error(f"Kesalahan saat memperbarui total stok untuk ID produk {product_id}: {e}", exc_info=True)

        finally:
            cursor.close()
            conn.close()
            logger.debug(f"Koneksi database ditutup untuk update_total_stock_from_variants {product_id}")


variant_service = VariantService()