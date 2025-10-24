import mysql.connector
from app.core.db import get_db_connection
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class CategoryService:
    

    def get_all_categories(self):
        logger.debug("Mengambil semua kategori")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute('SELECT * FROM categories ORDER BY name ASC')
            categories = cursor.fetchall()
            logger.info(f"Mengambil {len(categories)} kategori")
            return categories

        except Exception as e:
            logger.error(f"Kesalahan saat mengambil semua kategori: {e}", exc_info=True)
            raise

        finally:
            cursor.close()
            conn.close()
            logger.debug("Koneksi database ditutup untuk get_all_categories")


    def get_category_by_id(self, category_id):
        logger.debug(f"Mengambil kategori berdasarkan id: {category_id}")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute('SELECT * FROM categories WHERE id = %s', (category_id,))
            category = cursor.fetchone()

            if category:
                logger.info(f"Kategori ditemukan untuk id: {category_id}")
            else:
                logger.warning(f"Kategori tidak ditemukan untuk id: {category_id}")

            return category if category else None

        except Exception as e:
            logger.error(f"Kesalahan saat mengambil kategori id {category_id}: {e}", exc_info=True)
            raise

        finally:
            cursor.close()
            conn.close()
            logger.debug(f"Koneksi database ditutup untuk get_category_by_id {category_id}")


    def create_category(self, name):
        logger.debug(f"Mencoba membuat kategori dengan nama: {name}")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute('INSERT INTO categories (name) VALUES (%s)', (name,))
            new_id = cursor.lastrowid
            conn.commit()

            cursor.execute('SELECT * FROM categories WHERE id = %s', (new_id,))
            new_category = cursor.fetchone()

            logger.info(f"Kategori '{name}' berhasil dibuat dengan id: {new_id}")
            return {
                'success': True,
                'message': f'Kategori "{name}" berhasil ditambahkan.',
                'data': new_category
            }

        except mysql.connector.IntegrityError:
            conn.rollback()
            logger.warning(f"Gagal membuat kategori '{name}': Sudah ada.")
            return {
                'success': False,
                'message': f'Kategori "{name}" sudah ada.'
            }

        except Exception as e:
            conn.rollback()
            logger.error(f"Kesalahan saat membuat kategori '{name}': {e}", exc_info=True)
            return {
                'success': False,
                'message': f'Gagal membuat kategori "{name}".'
            }

        finally:
            cursor.close()
            conn.close()
            logger.debug(f"Koneksi database ditutup untuk create_category {name}")


    def update_category(self, category_id, name):
        logger.debug(f"Mencoba memperbarui id kategori: {category_id} menjadi nama: {name}")
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('UPDATE categories SET name = %s WHERE id = %s', (name, category_id))
            conn.commit()

            if cursor.rowcount > 0:
                logger.info(f"Kategori id {category_id} berhasil diperbarui menjadi '{name}'.")
                return {'success': True, 'message': 'Kategori berhasil diperbarui.'}
            else:
                logger.warning(f"Pembaruan kategori gagal: Kategori id {category_id} tidak ditemukan.")
                return {'success': False, 'message': 'Kategori tidak ditemukan.'}

        except mysql.connector.IntegrityError:
            conn.rollback()
            logger.warning(f"Gagal memperbarui kategori id {category_id}: Nama '{name}' sudah ada.")
            return {
                'success': False,
                'message': f'Nama Kategori "{name}" sudah ada.'
            }

        except Exception as e:
            conn.rollback()
            logger.error(f"Kesalahan saat memperbarui kategori id {category_id}: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'Gagal memperbarui kategori id {category_id}.'
            }

        finally:
            cursor.close()
            conn.close()
            logger.debug(f"Koneksi database ditutup untuk update_category {category_id}")


    def delete_category(self, category_id):
        logger.debug(f"Mencoba menghapus kategori id: {category_id}")
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('UPDATE products SET category_id = NULL WHERE category_id = %s', (category_id,))
            product_update_count = cursor.rowcount

            cursor.execute('DELETE FROM categories WHERE id = %s', (category_id,))
            delete_count = cursor.rowcount
            conn.commit()

            if delete_count > 0:
                logger.info(
                    f"Kategori id {category_id} berhasil dihapus. "
                    f"Memperbarui {product_update_count} produk."
                )
                return {'success': True, 'message': 'Kategori berhasil dihapus.'}
            else:
                logger.warning(f"Penghapusan kategori gagal: Kategori id {category_id} tidak ditemukan.")
                return {'success': False, 'message': 'Kategori tidak ditemukan.'}

        except Exception as e:
            conn.rollback()
            logger.error(f"Kesalahan saat menghapus kategori id {category_id}: {e}", exc_info=True)
            return {'success': False, 'message': 'Gagal menghapus kategori.'}

        finally:
            cursor.close()
            conn.close()
            logger.debug(f"Koneksi database ditutup untuk delete_category {category_id}")


category_service = CategoryService()