import os
import json
from flask import current_app
from db.db_config import get_db_connection
from utils.image_utils import save_compressed_image
from services.products.variant_service import variant_service


class ProductService:

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
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO products (
                        name, price, discount_price, description, category_id, colors, 
                        image_url, additional_image_urls, stock, has_variants, 
                        weight_grams, sku
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (form_data['name'], form_data['price'], form_data.get('discount_price') or None,
                     form_data['description'], form_data['category_id'], form_data.get('colors'),
                     main_image_url, json.dumps(additional_image_urls), stock, has_variants,
                     weight_grams, sku)
                )
                product_id = cursor.lastrowid
                new_product_row = conn.execute('SELECT p.*, c.name as category_name FROM products p LEFT JOIN categories c ON p.category_id = c.id WHERE p.id = ?', (product_id,)).fetchone()

            return {'success': True, 'message': 'Produk berhasil ditambahkan!', 'product': dict(new_product_row)}

        except conn.IntegrityError as e:
            if 'UNIQUE constraint failed: products.sku' in str(e):
                return {'success': False, 'message': f'SKU "{sku}" sudah ada. Harap gunakan SKU yang unik.'}
            return {'success': False, 'message': f'Terjadi kesalahan database: {e}'}
        finally:
            conn.close()

    def update_product(self, product_id, form_data, files):
        conn = get_db_connection()
        try:
            with conn:
                product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
                if not product:
                    return {'success': False, 'message': 'Produk tidak ditemukan.'}

                old_has_variants = product['has_variants']
                new_has_variants = 'has_variants' in form_data

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

                stock = product['stock']
                weight_grams = product['weight_grams']
                sku = product['sku']

                if not old_has_variants and new_has_variants:
                    initial_stock = product['stock'] if product['stock'] and product['stock'] > 0 else 0
                    initial_weight = product['weight_grams'] if product['weight_grams'] and product['weight_grams'] > 0 else 0
                    initial_sku = product['sku']

                    variant_service.add_variant(product_id, "STANDAR", initial_stock, initial_weight, initial_sku)

                    stock = initial_stock
                    weight_grams = 0
                    sku = None

                elif old_has_variants and not new_has_variants:
                    variant_service.delete_all_variants_for_product(product_id, conn)
                    stock = form_data.get('stock', 0)
                    weight_grams = form_data.get('weight_grams', 0)
                    sku = form_data.get('sku') or None

                else:
                    if not new_has_variants:
                        stock = form_data.get('stock', product['stock'])
                        weight_grams = form_data.get('weight_grams', product['weight_grams'])
                        sku = form_data.get('sku') or None
                    else:
                        stock = product['stock']
                        weight_grams = 0
                        sku = None

                conn.execute(
                    """
                    UPDATE products SET 
                        name=?, price=?, discount_price=?, description=?, category_id=?, colors=?, 
                        stock=?, image_url=?, additional_image_urls=?, has_variants=?, 
                        weight_grams=?, sku=? 
                    WHERE id=?
                    """,
                    (form_data['name'], form_data['price'], form_data.get('discount_price') or None,
                     form_data['description'], form_data['category_id'], form_data.get('colors'),
                     stock, final_main, json.dumps(final_additional), new_has_variants,
                     weight_grams, sku, product_id)
                )

            for img_file in images_to_delete:
                if img_file in all_current_images:
                    try:
                        os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], img_file))
                    except OSError as e:
                        print(f"Error saat menghapus file {img_file}: {e}")

            if new_has_variants:
                variant_service.update_total_stock_from_variants(product_id)

            return {'success': True, 'message': 'Produk berhasil diperbarui!'}
        except conn.IntegrityError as e:
            if 'UNIQUE constraint failed' in str(e):
                return {'success': False, 'message': 'SKU yang dimasukkan sudah ada. Harap gunakan SKU yang unik.'}
            return {'success': False, 'message': 'Terjadi kesalahan database.'}
        finally:
            if conn:
                conn.close()

    def delete_product(self, product_id):
        conn = get_db_connection()
        try:
            with conn:
                conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
            return {'success': True, 'message': 'Produk berhasil dihapus.'}
        finally:
            conn.close()


product_service = ProductService()