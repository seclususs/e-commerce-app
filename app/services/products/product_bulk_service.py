from app.core.db import get_db_connection
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ProductBulkService:
    
    
    def handle_bulk_product_action(self, action, selected_ids, category_id=None):
        logger.debug(
            f"Menangani aksi massal: {action} untuk ID produk: {selected_ids}, "
            f"ID Kategori: {category_id}"
        )

        if not action or not selected_ids:
            logger.warning("Aksi massal gagal: Tidak ada aksi atau ID produk yang dipilih.")
            return {'success': False, 'message': 'Tidak ada aksi atau produk yang dipilih.'}

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            placeholders = ', '.join(['%s'] * len(selected_ids))
            params = tuple(selected_ids)
            message = ''

            if action == 'delete':
                logger.info(f"Menjalankan hapus massal untuk ID produk: {selected_ids}")
                cursor.execute(f'DELETE FROM products WHERE id IN ({placeholders})', params)
                message = f'{cursor.rowcount} produk berhasil dihapus.'

            elif action == 'set_category' and category_id:
                logger.info(
                    f"Menjalankan penetapan kategori massal ke {category_id} untuk ID produk: {selected_ids}"
                )
                params_with_category = (category_id,) + params
                cursor.execute(
                    f'UPDATE products SET category_id = %s WHERE id IN ({placeholders})',
                    params_with_category
                )
                message = f'Kategori untuk {cursor.rowcount} produk berhasil diubah.'

            else:
                logger.warning(
                    f"Aksi massal gagal: Aksi '{action}' tidak valid atau category_id hilang."
                )
                return {'success': False, 'message': 'Aksi tidak valid atau data kurang.'}

            conn.commit()
            logger.info(f"Aksi massal '{action}' selesai berhasil. Pesan: {message}")
            return {'success': True, 'message': message}

        except Exception as e:
            conn.rollback()
            logger.error(
                f"Kesalahan saat aksi massal '{action}' untuk ID {selected_ids}: {e}",
                exc_info=True
            )
            return {'success': False, 'message': 'Terjadi kesalahan saat memproses aksi massal.'}

        finally:
            cursor.close()
            conn.close()
            logger.debug("Koneksi database ditutup untuk handle_bulk_product_action")


product_bulk_service = ProductBulkService()