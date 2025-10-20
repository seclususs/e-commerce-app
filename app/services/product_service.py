import os
import json
import uuid
from flask import current_app
from database.db_config import get_db_connection
from utils.image_utils import save_compressed_image
from datetime import datetime, timedelta

class ProductService:
    """
    Layanan untuk mengelola semua logika bisnis terkait produk, kategori, dan ulasan.
    """

    def get_available_stock(self, product_id, variant_id=None, conn=None):
        """Menghitung stok yang tersedia (stok asli - stok ditahan)."""
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        
        try:
            conn.execute("DELETE FROM stock_holds WHERE expires_at < CURRENT_TIMESTAMP")
            conn.commit()

            base_stock_query = "SELECT stock FROM {} WHERE id = ?".format(
                "product_variants" if variant_id else "products"
            )
            stock_id = variant_id if variant_id else product_id
            
            product_stock_row = conn.execute(base_stock_query, (stock_id,)).fetchone()
            if not product_stock_row:
                return 0

            product_stock = product_stock_row['stock']
            
            held_stock_query = "SELECT SUM(quantity) as held FROM stock_holds WHERE product_id = ?"
            params = [product_id]
            if variant_id:
                held_stock_query += " AND variant_id = ?"
                params.append(variant_id)

            held_stock_row = conn.execute(held_stock_query, tuple(params)).fetchone()
            
            held_stock = held_stock_row['held'] if held_stock_row and held_stock_row['held'] else 0
            return product_stock - held_stock
        finally:
            if close_conn:
                conn.close()

    def hold_stock_for_checkout(self, user_id, session_id, cart_items):
        """Membuat catatan penahanan stok selama 10 menit untuk item di keranjang."""
        conn = get_db_connection()
        try:
            with conn:
                if user_id:
                    conn.execute("DELETE FROM stock_holds WHERE user_id = ?", (user_id,))
                else:
                    conn.execute("DELETE FROM stock_holds WHERE session_id = ?", (session_id,))

                for item in cart_items:
                    available_stock = self.get_available_stock(item['id'], item.get('variant_id'), conn)
                    if item['quantity'] > available_stock:
                        size_info = f" (Ukuran: {item['size']})" if item.get('size') else ""
                        return {'success': False, 'message': f"Stok untuk '{item['name']}'{size_info} tidak mencukupi (tersisa {available_stock})."}

                expires_at = datetime.now() + timedelta(minutes=10)
                for item in cart_items:
                    conn.execute(
                        "INSERT INTO stock_holds (user_id, session_id, product_id, variant_id, quantity, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (user_id, session_id, item['id'], item.get('variant_id'), item['quantity'], expires_at)
                    )
            return {'success': True, 'expires_at': expires_at.isoformat()}
        except Exception as e:
            print(f"Error holding stock: {e}")
            return {'success': False, 'message': 'Terjadi kesalahan saat validasi stok.'}
        finally:
            conn.close()

    def release_stock_holds(self, user_id, session_id, conn):
        """Melepas penahanan stok untuk user/sesi tertentu."""
        if user_id:
            conn.execute("DELETE FROM stock_holds WHERE user_id = ?", (user_id,))
        elif session_id:
            conn.execute("DELETE FROM stock_holds WHERE session_id = ?", (session_id,))

    def get_filtered_products(self, filters):
        conn = get_db_connection()
        try:
            query = "SELECT p.*, c.name as category_name FROM products p LEFT JOIN categories c ON p.category_id = c.id WHERE 1=1"
            params = []
            
            if filters.get('search'):
                query += " AND p.name LIKE ?"
                params.append(f'%{filters["search"]}%')
            if filters.get('category'):
                query += " AND p.category_id = ?"
                params.append(filters['category'])
            
            sort_by = filters.get('sort', 'popularity')
            if sort_by == 'price_asc':
                query += " ORDER BY CASE WHEN p.discount_price IS NOT NULL AND p.discount_price > 0 THEN p.discount_price ELSE p.price END ASC"
            elif sort_by == 'price_desc':
                query += " ORDER BY CASE WHEN p.discount_price IS NOT NULL AND p.discount_price > 0 THEN p.discount_price ELSE p.price END DESC"
            else:
                query += " ORDER BY p.popularity DESC"
                
            products = conn.execute(query, params).fetchall()
            return [dict(p) for p in products]
        finally:
            conn.close()

    def get_all_products_with_category(self):
        conn = get_db_connection()
        products = conn.execute('SELECT p.*, c.name as category_name FROM products p LEFT JOIN categories c ON p.category_id = c.id ORDER BY p.id DESC').fetchall()
        conn.close()
        return [dict(p) for p in products]

    def get_product_by_id(self, product_id):
        conn = get_db_connection()
        try:
            product_row = conn.execute('SELECT p.*, c.name as category_name FROM products p LEFT JOIN categories c ON p.category_id = c.id WHERE p.id = ?', (product_id,)).fetchone()
            if not product_row:
                return None
            
            product = dict(product_row)
            conn.execute('UPDATE products SET popularity = popularity + 1 WHERE id = ?', (product_id,))
            conn.commit()

            try:
                product['additional_image_urls'] = json.loads(product['additional_image_urls']) if product['additional_image_urls'] else []
            except (json.JSONDecodeError, TypeError):
                product['additional_image_urls'] = []
            product['all_images'] = [product['image_url']] + product['additional_image_urls']
            
            if product['has_variants']:
                product['variants'] = [dict(v) for v in self.get_variants_for_product(product_id, conn)]
                product['available_stock'] = sum(v['stock'] for v in product['variants'])
            else:
                product['variants'] = []
                product['available_stock'] = self.get_available_stock(product_id, conn=conn)

            return product
        finally:
            conn.close()

    def get_reviews_for_product(self, product_id):
        conn = get_db_connection()
        reviews = conn.execute("SELECT r.*, u.username FROM reviews r JOIN users u ON r.user_id = u.id WHERE r.product_id = ? ORDER BY r.created_at DESC", (product_id,)).fetchall()
        conn.close()
        return [dict(r) for r in reviews]

    def check_user_can_review(self, user_id, product_id):
        conn = get_db_connection()
        try:
            has_purchased = conn.execute("SELECT 1 FROM orders o JOIN order_items oi ON o.id = oi.order_id WHERE o.user_id = ? AND oi.product_id = ? AND o.status = 'Completed' LIMIT 1", (user_id, product_id)).fetchone()
            if has_purchased:
                has_reviewed = conn.execute('SELECT 1 FROM reviews WHERE user_id = ? AND product_id = ? LIMIT 1', (user_id, product_id)).fetchone()
                return not has_reviewed
            return False
        finally:
            conn.close()

    def add_review(self, user_id, product_id, rating, comment):
        if not self.check_user_can_review(user_id, product_id):
            return {'success': False, 'message': 'Anda tidak dapat memberikan ulasan untuk produk ini.'}
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO reviews (product_id, user_id, rating, comment) VALUES (?, ?, ?, ?)', (product_id, user_id, rating, comment))
            conn.commit()
            return {'success': True, 'message': 'Terima kasih atas ulasan Anda!'}
        finally:
            conn.close()

    def create_product(self, form_data, files):
        images = files.getlist("images")
        main_image_identifier = form_data.get('main_image')

        if not images or all(f.filename == '' for f in images):
            return {'success': False, 'message': 'Anda harus mengunggah setidaknya satu gambar.'}
        if not main_image_identifier:
            return {'success': False, 'message': 'Anda harus memilih satu gambar sebagai gambar utama.'}

        saved_filenames = {img.filename: save_compressed_image(img) for img in images if img}
        saved_filenames = {k: v for k, v in saved_filenames.items() if v}
        
        main_image_url = saved_filenames.get(main_image_identifier)
        if not main_image_url:
            return {'success': False, 'message': 'Gambar utama yang dipilih tidak valid atau gagal diproses.'}

        additional_image_urls = [fname for orig, fname in saved_filenames.items() if orig != main_image_identifier]
        has_variants = 'has_variants' in form_data
        stock = 0 if has_variants else form_data.get('stock', 10)
        weight_grams = 0 if has_variants else form_data.get('weight_grams', 0)
        sku = form_data.get('sku') or None

        conn = get_db_connection()
        try:
            with conn:
                conn.execute(
                    'INSERT INTO products (name, price, discount_price, description, category_id, colors, image_url, additional_image_urls, stock, has_variants, weight_grams, sku) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                    (form_data['name'], form_data['price'], form_data.get('discount_price') or None, form_data['description'], 
                     form_data['category_id'], form_data.get('colors'), main_image_url, json.dumps(additional_image_urls), stock, has_variants, weight_grams, sku)
                )
            return {'success': True, 'message': 'Produk berhasil ditambahkan!'}
        except conn.IntegrityError as e:
            if 'UNIQUE constraint failed: products.sku' in str(e):
                return {'success': False, 'message': f'SKU "{sku}" sudah ada. Harap gunakan SKU yang unik.'}
            return {'success': False, 'message': 'Terjadi kesalahan database.'}
        finally:
            conn.close()
    
    def update_product(self, product_id, form_data, files):
        conn = get_db_connection()
        try:
            with conn:
                product = conn.execute('SELECT image_url, additional_image_urls, has_variants FROM products WHERE id = ?', (product_id,)).fetchone()
                if not product:
                    return {'success': False, 'message': 'Produk tidak ditemukan.'}

                existing_additional = json.loads(product['additional_image_urls']) if product['additional_image_urls'] else []
                all_current_images = [product['image_url']] + existing_additional
                
                images_to_delete = form_data.getlist('delete_image')
                remaining_images = [img for img in all_current_images if img not in images_to_delete]

                new_images = files.getlist("new_images")
                newly_saved = [save_compressed_image(img) for img in new_images if img]
                newly_saved = [name for name in newly_saved if name]

                final_pool = remaining_images + newly_saved
                if not final_pool:
                    return {'success': False, 'message': 'Produk harus memiliki setidaknya satu gambar.'}

                new_main_image = form_data.get('main_image')
                final_main = new_main_image if new_main_image in final_pool else final_pool[0]
                final_additional = [img for img in final_pool if img != final_main]
                
                has_variants = 'has_variants' in form_data
                stock = form_data.get('stock', 0) if not has_variants else product['stock']
                weight_grams = form_data.get('weight_grams', 0) if not has_variants else 0
                sku = form_data.get('sku') or None

                if product['has_variants'] and not has_variants:
                    self.delete_all_variants_for_product(product_id, conn)

                conn.execute(
                    'UPDATE products SET name=?, price=?, discount_price=?, description=?, category_id=?, colors=?, stock=?, image_url=?, additional_image_urls=?, has_variants=?, weight_grams=?, sku=? WHERE id=?', 
                    (form_data['name'], form_data['price'], form_data.get('discount_price') or None, form_data['description'], form_data['category_id'], 
                     form_data.get('colors'), stock, final_main, json.dumps(final_additional), has_variants, weight_grams, sku, product_id)
                )

            for img_file in images_to_delete:
                try: os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], img_file))
                except OSError as e: print(f"Error saat menghapus file {img_file}: {e}")
            
            return {'success': True, 'message': 'Produk berhasil diperbarui!'}
        except conn.IntegrityError as e:
            if 'UNIQUE constraint failed: products.sku' in str(e):
                return {'success': False, 'message': f'SKU "{sku}" sudah ada. Harap gunakan SKU yang unik.'}
            return {'success': False, 'message': 'Terjadi kesalahan database.'}
        finally:
            conn.close()

    def delete_product(self, product_id):
        conn = get_db_connection()
        try:
            with conn:
                conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
            return {'success': True, 'message': 'Produk berhasil dihapus.'}
        finally:
            conn.close()

    def handle_bulk_product_action(self, action, selected_ids, category_id=None):
        if not action or not selected_ids:
            return {'success': False, 'message': 'Tidak ada aksi atau produk yang dipilih.'}
        conn = get_db_connection()
        try:
            placeholders = ', '.join(['?'] * len(selected_ids))
            if action == 'delete':
                conn.execute(f'DELETE FROM products WHERE id IN ({placeholders})', selected_ids)
                message = f'{len(selected_ids)} produk berhasil dihapus.'
            elif action == 'set_category' and category_id:
                conn.execute(f'UPDATE products SET category_id = ? WHERE id IN ({placeholders})', [category_id] + selected_ids)
                message = f'Kategori untuk {len(selected_ids)} produk berhasil diubah.'
            else:
                return {'success': False, 'message': 'Aksi tidak valid atau data kurang.'}
            conn.commit()
            return {'success': True, 'message': message}
        finally:
            conn.close()

    # Logika Varian
    def get_variants_for_product(self, product_id, conn=None):
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        try:
            return conn.execute("SELECT * FROM product_variants WHERE product_id = ? ORDER BY id", (product_id,)).fetchall()
        finally:
            if close_conn:
                conn.close()
    
    def add_variant(self, product_id, size, stock, weight_grams, sku):
        if not size or not stock or int(stock) < 0 or not weight_grams or int(weight_grams) < 0:
            return {'success': False, 'message': 'Ukuran, stok, dan berat harus diisi dengan benar.'}
        conn = get_db_connection()
        try:
            with conn:
                conn.execute("INSERT INTO product_variants (product_id, size, stock, weight_grams, sku) VALUES (?, ?, ?, ?, ?)", (product_id, size.upper(), stock, weight_grams, sku.upper() if sku else None))
            return {'success': True, 'message': f'Varian {size.upper()} berhasil ditambahkan.'}
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
            
    def get_related_products(self, product_id, category_id):
        conn = get_db_connection()
        try:
            query = """
                SELECT p.*, c.name as category_name 
                FROM products p 
                LEFT JOIN categories c ON p.category_id = c.id 
                WHERE p.category_id = ? AND p.id != ?
                ORDER BY p.popularity DESC 
                LIMIT 4
            """
            related_products = conn.execute(query, (category_id, product_id)).fetchall()
            return [dict(p) for p in related_products]
        finally:
            conn.close()

    # Logika Kategori
    def get_all_categories(self):
        conn = get_db_connection()
        categories = conn.execute('SELECT * FROM categories ORDER BY name ASC').fetchall()
        conn.close()
        return [dict(c) for c in categories]

    def create_category(self, name):
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO categories (name) VALUES (?)', (name,))
            conn.commit()
            return {'success': True, 'message': f'Kategori "{name}" berhasil ditambahkan.'}
        except conn.IntegrityError:
            return {'success': False, 'message': f'Kategori "{name}" sudah ada.'}
        finally:
            conn.close()

    def update_category(self, category_id, name):
        conn = get_db_connection()
        conn.execute('UPDATE categories SET name = ? WHERE id = ?', (name, category_id))
        conn.commit()
        conn.close()
        return {'success': True, 'message': 'Kategori berhasil diperbarui.'}

    def delete_category(self, category_id):
        conn = get_db_connection()
        try:
            conn.execute('UPDATE products SET category_id = NULL WHERE category_id = ?', (category_id,))
            conn.execute('DELETE FROM categories WHERE id = ?', (category_id,))
            conn.commit()
            return {'success': True, 'message': 'Kategori berhasil dihapus.'}
        finally:
            conn.close()

product_service = ProductService()