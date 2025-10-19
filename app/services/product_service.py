import os
import json
import uuid
from flask import current_app
from database.db_config import get_db_connection
from utils.image_utils import save_compressed_image

class ProductService:
    """
    Layanan untuk mengelola semua logika bisnis terkait produk, kategori, dan ulasan.
    """

    def get_filtered_products(self, filters):
        """
        Menangani logika filter, pencarian, dan pengurutan produk.
        'filters' adalah dict yang bisa berisi 'search', 'category', 'sort'.
        """
        conn = get_db_connection()
        try:
            query = "SELECT p.*, c.name as category_name FROM products p LEFT JOIN categories c ON p.category_id = c.id WHERE 1=1"
            params = []
            
            search_term = filters.get('search')
            category_id = filters.get('category')
            sort_by = filters.get('sort', 'popularity')

            if search_term:
                query += " AND p.name LIKE ?"
                params.append(f'%{search_term}%')
            if category_id:
                query += " AND p.category_id = ?"
                params.append(category_id)
            
            if sort_by == 'price_asc':
                query += " ORDER BY CASE WHEN p.discount_price IS NOT NULL AND p.discount_price > 0 THEN p.discount_price ELSE p.price END ASC"
            elif sort_by == 'price_desc':
                query += " ORDER BY CASE WHEN p.discount_price IS NOT NULL AND p.discount_price > 0 THEN p.discount_price ELSE p.price END DESC"
            else: # Default sorting
                query += " ORDER BY p.popularity DESC"
                
            products = conn.execute(query, params).fetchall()
            return [dict(p) for p in products]
        finally:
            conn.close()

    def get_all_products_with_category(self):
        """Mengambil semua produk dengan nama kategorinya untuk halaman admin."""
        conn = get_db_connection()
        products = conn.execute('SELECT p.*, c.name as category_name FROM products p LEFT JOIN categories c ON p.category_id = c.id ORDER BY p.id DESC').fetchall()
        conn.close()
        return [dict(p) for p in products]

    def get_product_by_id(self, product_id):
        """Mengambil detail produk tunggal berdasarkan ID."""
        conn = get_db_connection()
        try:
            product_row = conn.execute('SELECT p.*, c.name as category_name FROM products p LEFT JOIN categories c ON p.category_id = c.id WHERE p.id = ?', (product_id,)).fetchone()
            if product_row:
                product = dict(product_row)
                # Tingkatkan popularitas
                conn.execute('UPDATE products SET popularity = popularity + 1 WHERE id = ?', (product_id,))
                conn.commit()

                # Proses gambar tambahan
                try:
                    product['additional_image_urls'] = json.loads(product['additional_image_urls']) if product['additional_image_urls'] else []
                except (json.JSONDecodeError, TypeError):
                    product['additional_image_urls'] = []
                product['all_images'] = [product['image_url']] + product['additional_image_urls']
                return product
            return None
        finally:
            conn.close()

    def get_reviews_for_product(self, product_id):
        """Mengambil semua ulasan untuk produk tertentu."""
        conn = get_db_connection()
        reviews = conn.execute("""
            SELECT r.*, u.username FROM reviews r 
            JOIN users u ON r.user_id = u.id 
            WHERE r.product_id = ? ORDER BY r.created_at DESC
        """, (product_id,)).fetchall()
        conn.close()
        return [dict(r) for r in reviews]

    def check_user_can_review(self, user_id, product_id):
        """Memeriksa apakah pengguna bisa memberikan ulasan (telah membeli & belum mengulas)."""
        conn = get_db_connection()
        try:
            has_purchased = conn.execute("""
                SELECT 1 FROM orders o
                JOIN order_items oi ON o.id = oi.order_id
                WHERE o.user_id = ? AND oi.product_id = ? AND o.status = 'Completed'
                LIMIT 1
            """, (user_id, product_id)).fetchone()

            if has_purchased:
                has_reviewed = conn.execute(
                    'SELECT 1 FROM reviews WHERE user_id = ? AND product_id = ? LIMIT 1',
                    (user_id, product_id)
                ).fetchone()
                return not has_reviewed
            return False
        finally:
            conn.close()

    def add_review(self, user_id, product_id, rating, comment):
        """Menambahkan ulasan baru ke database setelah validasi."""
        if not self.check_user_can_review(user_id, product_id):
            return {'success': False, 'message': 'Anda tidak dapat memberikan ulasan untuk produk ini.'}
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO reviews (product_id, user_id, rating, comment) VALUES (?, ?, ?, ?)', 
                         (product_id, user_id, rating, comment))
            conn.commit()
            return {'success': True, 'message': 'Terima kasih atas ulasan Anda!'}
        finally:
            conn.close()

    def create_product(self, form_data, files):
        """Membuat produk baru, termasuk memproses gambar."""
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

        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO products (name, price, discount_price, description, category_id, sizes, colors, image_url, additional_image_urls, stock) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                (form_data['name'], form_data['price'], form_data.get('discount_price') or None, form_data['description'], 
                 form_data['category_id'], form_data['sizes'], form_data['colors'], main_image_url, json.dumps(additional_image_urls), form_data['stock'])
            )
            conn.commit()
            return {'success': True, 'message': 'Produk berhasil ditambahkan!'}
        finally:
            conn.close()
    
    def update_product(self, product_id, form_data, files):
        """Memperbarui produk yang ada, termasuk menangani upload dan penghapusan gambar."""
        conn = get_db_connection()
        try:
            product = conn.execute('SELECT image_url, additional_image_urls FROM products WHERE id = ?', (product_id,)).fetchone()
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

            conn.execute(
                'UPDATE products SET name=?, price=?, discount_price=?, description=?, category_id=?, sizes=?, colors=?, stock=?, image_url=?, additional_image_urls=? WHERE id=?', 
                (form_data['name'], form_data['price'], form_data.get('discount_price') or None, form_data['description'], form_data['category_id'], 
                 form_data['sizes'], form_data['colors'], form_data['stock'], final_main, json.dumps(final_additional), product_id)
            )
            conn.commit()

            for img_file in images_to_delete:
                try:
                    os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], img_file))
                except OSError as e:
                    print(f"Error saat menghapus file {img_file}: {e}")
            
            return {'success': True, 'message': 'Produk berhasil diperbarui!'}
        finally:
            conn.close()

    def delete_product(self, product_id):
        """Menghapus produk dari database."""
        conn = get_db_connection()
        conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
        conn.commit()
        conn.close()

    def handle_bulk_product_action(self, action, selected_ids, category_id=None):
        """Menangani aksi massal untuk produk."""
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

    # --- Logika Kategori ---
    def get_all_categories(self):
        """Mengambil semua kategori produk."""
        conn = get_db_connection()
        categories = conn.execute('SELECT * FROM categories ORDER BY name ASC').fetchall()
        conn.close()
        return [dict(c) for c in categories]

    def create_category(self, name):
        """Membuat kategori baru."""
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
        """Memperbarui nama kategori."""
        conn = get_db_connection()
        conn.execute('UPDATE categories SET name = ? WHERE id = ?', (name, category_id))
        conn.commit()
        conn.close()
        return {'success': True, 'message': 'Kategori berhasil diperbarui.'}

    def delete_category(self, category_id):
        """Menghapus kategori dan mengatur ulang produk terkait."""
        conn = get_db_connection()
        try:
            # Set category_id produk terkait menjadi NULL
            conn.execute('UPDATE products SET category_id = NULL WHERE category_id = ?', (category_id,))
            conn.execute('DELETE FROM categories WHERE id = ?', (category_id,))
            conn.commit()
            return {'success': True, 'message': 'Kategori berhasil dihapus.'}
        finally:
            conn.close()

product_service = ProductService()