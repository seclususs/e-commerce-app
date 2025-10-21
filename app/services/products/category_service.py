from db.db_config import get_db_connection

class CategoryService:
    """
    Layanan untuk mengelola semua logika bisnis terkait kategori produk.
    """

    def get_all_categories(self):
        """Mengambil semua kategori dari database."""
        conn = get_db_connection()
        categories = conn.execute('SELECT * FROM categories ORDER BY name ASC').fetchall()
        conn.close()
        return [dict(c) for c in categories]

    def get_category_by_id(self, category_id):
        """Mengambil satu kategori berdasarkan ID."""
        conn = get_db_connection()
        category = conn.execute('SELECT * FROM categories WHERE id = ?', (category_id,)).fetchone()
        conn.close()
        return dict(category) if category else None

    def create_category(self, name):
        """Membuat kategori baru dan mengembalikan data lengkapnya."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO categories (name) VALUES (?)', (name,))
            new_id = cursor.lastrowid
            conn.commit()
            new_category = conn.execute('SELECT * FROM categories WHERE id = ?', (new_id,)).fetchone()
            return {'success': True, 'message': f'Kategori "{name}" berhasil ditambahkan.', 'data': dict(new_category)}
        except conn.IntegrityError:
            return {'success': False, 'message': f'Kategori "{name}" sudah ada.'}
        finally:
            conn.close()

    def update_category(self, category_id, name):
        """Memperbarui nama kategori yang sudah ada."""
        conn = get_db_connection()
        try:
            conn.execute('UPDATE categories SET name = ? WHERE id = ?', (name, category_id))
            conn.commit()
            return {'success': True, 'message': 'Kategori berhasil diperbarui.'}
        except conn.IntegrityError:
            return {'success': False, 'message': f'Nama Kategori "{name}" sudah ada.'}
        finally:
            conn.close()

    def delete_category(self, category_id):
        """Menghapus kategori dan memutuskan relasinya dengan produk."""
        conn = get_db_connection()
        try:
            # Set category_id di produk menjadi NULL sebelum menghapus kategori
            conn.execute('UPDATE products SET category_id = NULL WHERE category_id = ?', (category_id,))
            conn.execute('DELETE FROM categories WHERE id = ?', (category_id,))
            conn.commit()
            return {'success': True, 'message': 'Kategori berhasil dihapus.'}
        finally:
            conn.close()

category_service = CategoryService()