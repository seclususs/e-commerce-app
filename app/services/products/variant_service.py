from app.core.db import get_db_connection


class VariantService:

    def get_variants_for_product(self, product_id, conn=None):
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            variants = conn.execute("SELECT * FROM product_variants WHERE product_id = ? ORDER BY id", (product_id,)).fetchall()
            return [dict(v) for v in variants]
        finally:
            if close_conn:
                conn.close()

    def add_variant(self, product_id, size, stock, weight_grams, sku):
        if not size or not stock or int(stock) < 0 or not weight_grams or int(weight_grams) < 0:
            return {'success': False, 'message': 'Ukuran, stok, dan berat harus diisi dengan benar.'}
        conn = get_db_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO product_variants (product_id, size, stock, weight_grams, sku) VALUES (?, ?, ?, ?, ?)", (product_id, size.upper(), stock, weight_grams, sku.upper() if sku else None))
                new_id = cursor.lastrowid
                new_variant = conn.execute("SELECT * FROM product_variants WHERE id = ?", (new_id,)).fetchone()
            return {'success': True, 'message': f'Varian {size.upper()} berhasil ditambahkan.', 'data': dict(new_variant)}
        except conn.IntegrityError as e:
            if 'UNIQUE constraint failed: product_variants.sku' in str(e):
                return {'success': False, 'message': f'SKU "{sku}" sudah ada. Harap gunakan SKU yang unik.'}
            return {'success': False, 'message': 'Terjadi kesalahan database.'}
        finally:
            conn.close()

    def update_variant(self, variant_id, size, stock, weight_grams, sku):
        if not size or not stock or int(stock) < 0 or not weight_grams or int(weight_grams) < 0:
            return {'success': False, 'message': 'Ukuran, stok, dan berat harus diisi dengan benar.'}
        conn = get_db_connection()
        try:
            with conn:
                conn.execute("UPDATE product_variants SET size = ?, stock = ?, weight_grams = ?, sku = ? WHERE id = ?", (size.upper(), stock, weight_grams, sku.upper() if sku else None, variant_id))
            return {'success': True, 'message': 'Varian berhasil diperbarui.'}
        except conn.IntegrityError as e:
            if 'UNIQUE constraint failed: product_variants.sku' in str(e):
                return {'success': False, 'message': f'SKU "{sku}" sudah ada. Harap gunakan SKU yang unik.'}
            return {'success': False, 'message': 'Terjadi kesalahan database.'}
        finally:
            conn.close()

    def delete_variant(self, variant_id):
        conn = get_db_connection()
        try:
            conn.execute("DELETE FROM product_variants WHERE id = ?", (variant_id,))
            conn.commit()
            return {'success': True, 'message': 'Varian berhasil dihapus.'}
        finally:
            conn.close()

    def delete_all_variants_for_product(self, product_id, conn):
        conn.execute("DELETE FROM product_variants WHERE product_id = ?", (product_id,))

    def update_total_stock_from_variants(self, product_id):
        conn = get_db_connection()
        try:
            total_stock = conn.execute("SELECT SUM(stock) FROM product_variants WHERE product_id = ?", (product_id,)).fetchone()[0]
            conn.execute("UPDATE products SET stock = ? WHERE id = ?", (total_stock or 0, product_id))
            conn.commit()
        finally:
            conn.close()


variant_service = VariantService()