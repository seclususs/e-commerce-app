from db.db_config import get_db_connection

class ProductBulkService:
    """
    Layanan untuk menangani aksi massal pada produk.
    """
    def handle_bulk_product_action(self, action, selected_ids, category_id=None):
        """Menangani aksi massal (hapus, ubah kategori) pada produk."""
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

product_bulk_service = ProductBulkService()