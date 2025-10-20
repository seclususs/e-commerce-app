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
        """Memperbarui nama kategori yang sudah ada."""
        conn = get_db_connection()
        conn.execute('UPDATE categories SET name = ? WHERE id = ?', (name, category_id))
        conn.commit()
        conn.close()
        return {'success': True, 'message': 'Kategori berhasil diperbarui.'}

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