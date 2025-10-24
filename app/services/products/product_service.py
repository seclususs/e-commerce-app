import os
import json
import mysql.connector
from flask import current_app
from app.core.db import get_db_connection
from app.utils.image_utils import save_compressed_image
from app.services.products.variant_service import variant_service
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ProductService:
    
    
    def create_product(self, form_data, files):
        logger.debug(f"Mencoba membuat produk dengan data formulir: {form_data.keys()}")
        images = files.getlist("images")
        main_image_identifier = form_data.get('main_image')

        if not images or all(f.filename == '' for f in images):
            logger.warning("Pembuatan produk gagal: Tidak ada gambar yang diunggah.")
            return {'success': False, 'message': 'Anda harus mengunggah setidaknya satu gambar.'}

        if not main_image_identifier:
            logger.warning("Pembuatan produk gagal: Tidak ada gambar utama yang dipilih.")
            return {'success': False, 'message': 'Anda harus memilih satu gambar sebagai gambar utama.'}

        saved_filenames = {
            img.filename: save_compressed_image(img) for img in images if img
        }
        saved_filenames = {k: v for k, v in saved_filenames.items() if v}
        logger.debug(f"Nama file gambar yang disimpan: {saved_filenames}")

        main_image_url = saved_filenames.get(main_image_identifier)
        if not main_image_url:
            logger.error(
                f"Pembuatan produk gagal: Gambar utama '{main_image_identifier}' "
                "gagal diproses atau tidak ditemukan di file yang disimpan."
            )
            return {'success': False, 'message': 'Gambar utama yang dipilih tidak valid atau gagal diproses.'}

        additional_image_urls = [
            fname for orig, fname in saved_filenames.items() if orig != main_image_identifier
        ]
        has_variants = 'has_variants' in form_data
        stock = 0 if has_variants else form_data.get('stock', 10)
        weight_grams = 0 if has_variants else form_data.get('weight_grams', 0)
        sku = form_data.get('sku') or None

        logger.debug(
            f"Detail produk - Memiliki Varian: {has_variants}, Stok: {stock}, "
            f"Berat: {weight_grams}, SKU: {sku}"
        )

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(
                """
                INSERT INTO products (
                    name, price, discount_price, description, category_id, colors,
                    image_url, additional_image_urls, stock, has_variants,
                    weight_grams, sku
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    form_data['name'], form_data['price'], form_data.get('discount_price') or None,
                    form_data['description'], form_data['category_id'], form_data.get('colors'),
                    main_image_url, json.dumps(additional_image_urls), stock, has_variants,
                    weight_grams, sku.upper() if sku else None
                )
            )
            product_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Produk '{form_data['name']}' berhasil dibuat dengan ID: {product_id}")

            cursor.execute(
                """
                SELECT p.*, c.name AS category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.id = %s
                """,
                (product_id,)
            )
            new_product_row = cursor.fetchone()

            return {'success': True, 'message': 'Produk berhasil ditambahkan!', 'product': new_product_row}

        except mysql.connector.IntegrityError as e:
            conn.rollback()
            if e.errno == 1062:
                logger.warning(f"Pembuatan produk gagal: SKU duplikat '{sku}'.")
                return {'success': False, 'message': f'SKU "{sku}" sudah ada. Harap gunakan SKU yang unik.'}

            logger.error(f"Kesalahan integritas database saat pembuatan produk: {e}", exc_info=True)
            return {'success': False, 'message': f'Terjadi kesalahan database: {e}'}

        except Exception as e:
            conn.rollback()
            logger.error(f"Kesalahan tak terduga saat pembuatan produk: {e}", exc_info=True)
            return {'success': False, 'message': 'Gagal menambahkan produk.'}

        finally:
            cursor.close()
            conn.close()
            logger.debug("Koneksi database ditutup untuk create_product")


    def update_product(self, product_id, form_data, files):
        logger.debug(f"Mencoba memperbarui ID produk: {product_id} dengan data formulir: {form_data.keys()}")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute('SELECT * FROM products WHERE id = %s', (product_id,))
            product = cursor.fetchone()

            if not product:
                logger.warning(f"Pembaruan produk gagal: ID Produk {product_id} tidak ditemukan.")
                return {'success': False, 'message': 'Produk tidak ditemukan.'}

            old_has_variants = product['has_variants']
            new_has_variants = 'has_variants' in form_data
            logger.debug(f"Perubahan status varian: {old_has_variants} -> {new_has_variants}")

            existing_additional = (
                json.loads(product['additional_image_urls'])
                if product['additional_image_urls'] else []
            )
            all_current_images = [product['image_url']] + existing_additional
            images_to_delete = form_data.getlist('delete_image')
            logger.debug(f"Gambar yang ditandai untuk dihapus: {images_to_delete}")

            remaining_images = [img for img in all_current_images if img not in images_to_delete]
            new_images = files.getlist("new_images")
            newly_saved = [save_compressed_image(img) for img in new_images if img]
            newly_saved = [name for name in newly_saved if name]
            logger.debug(f"Gambar yang baru disimpan: {newly_saved}")

            final_pool = remaining_images + newly_saved

            if not final_pool:
                logger.warning(f"Pembaruan produk gagal untuk ID {product_id}: Tidak ada gambar yang akan tersisa setelah pembaruan.")
                return {'success': False, 'message': 'Produk harus memiliki setidaknya satu gambar.'}

            new_main_image = form_data.get('main_image')
            final_main = new_main_image if new_main_image in final_pool else final_pool[0]
            final_additional = [img for img in final_pool if img != final_main]
            logger.debug(f"Gambar final - Utama: {final_main}, Tambahan: {final_additional}")

            stock = product['stock']
            weight_grams = product['weight_grams']
            sku = product['sku']

            if not old_has_variants and new_has_variants:
                logger.info(
                    f"Mengonversi produk {product_id} menjadi produk varian. "
                    "Membuat varian 'STANDAR' awal."
                )
                initial_stock = product['stock'] if product['stock'] and product['stock'] > 0 else 0
                initial_weight = product['weight_grams'] if product['weight_grams'] and product['weight_grams'] > 0 else 0
                initial_sku = product['sku']

                variant_result = variant_service.add_variant(
                    product_id, "STANDAR", initial_stock, initial_weight,
                    initial_sku.upper() if initial_sku else None
                )

                if not variant_result['success'] and 'sudah ada' not in variant_result['message']:
                    logger.warning(
                        f"Gagal membuat varian awal untuk produk {product_id}: {variant_result['message']}"
                    )

                stock = initial_stock
                weight_grams = 0
                sku = None

            elif old_has_variants and not new_has_variants:
                logger.info(
                    f"Mengonversi produk {product_id} dari varian ke non-varian. "
                    "Menghapus varian yang ada."
                )
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

            logger.debug(f"Detail produk final - Stok: {stock}, Berat: {weight_grams}, SKU: {sku}")

            cursor.execute(
                """
                UPDATE products SET
                    name=%s, price=%s, discount_price=%s, description=%s, category_id=%s, colors=%s,
                    stock=%s, image_url=%s, additional_image_urls=%s, has_variants=%s,
                    weight_grams=%s, sku=%s
                WHERE id=%s
                """,
                (
                    form_data['name'], form_data['price'], form_data.get('discount_price') or None,
                    form_data['description'], form_data['category_id'], form_data.get('colors'),
                    stock, final_main, json.dumps(final_additional), new_has_variants,
                    weight_grams, sku.upper() if sku else None, product_id
                )
            )
            conn.commit()

            for img_file in images_to_delete:
                if img_file in all_current_images:
                    try:
                        file_path = os.path.join(current_app.config['IMAGE_FOLDER'], img_file)
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            logger.info(f"File gambar yang dihapus: {img_file}")
                        else:
                            logger.warning(f"File gambar tidak ditemukan untuk dihapus: {img_file}")
                    except OSError as e:
                        logger.error(f"Kesalahan saat menghapus file gambar {img_file}: {e}", exc_info=True)

            if new_has_variants:
                logger.debug(f"Memperbarui total stok dari varian untuk ID produk {product_id}")
                variant_service.update_total_stock_from_variants(product_id)

            logger.info(f"ID Produk {product_id} berhasil diperbarui.")
            return {'success': True, 'message': 'Produk berhasil diperbarui!'}

        except mysql.connector.IntegrityError as e:
            conn.rollback()
            if e.errno == 1062:
                logger.warning(f"Pembaruan produk gagal untuk ID {product_id}: SKU duplikat '{sku}'.")
                return {'success': False, 'message': 'SKU yang dimasukkan sudah ada. Harap gunakan SKU yang unik.'}

            logger.error(f"Kesalahan integritas database saat pembaruan produk untuk ID {product_id}: {e}", exc_info=True)
            return {'success': False, 'message': 'Terjadi kesalahan database.'}

        except Exception as e:
            conn.rollback()
            logger.error(f"Kesalahan tak terduga saat memperbarui ID produk {product_id}: {e}", exc_info=True)
            return {'success': False, 'message': 'Gagal memperbarui produk.'}

        finally:
            cursor.close()
            conn.close()
            logger.debug(f"Koneksi database ditutup untuk update_product {product_id}")


    def delete_product(self, product_id):
        logger.debug(f"Mencoba menghapus ID produk: {product_id}")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(
                "SELECT image_url, additional_image_urls FROM products WHERE id = %s",
                (product_id,)
            )
            product = cursor.fetchone()

            cursor.execute('DELETE FROM products WHERE id = %s', (product_id,))
            deleted_count = cursor.rowcount
            conn.commit()

            if deleted_count > 0:
                logger.info(f"Data produk ID {product_id} berhasil dihapus.")

                if product:
                    images_to_delete = [product['image_url']]
                    if product['additional_image_urls']:
                        try:
                            additional = json.loads(product['additional_image_urls'])
                            images_to_delete.extend(additional)
                        except (json.JSONDecodeError, TypeError):
                            logger.warning(f"Tidak dapat mem-parsing additional_image_urls untuk produk {product_id} yang dihapus")

                    image_folder = current_app.config['IMAGE_FOLDER']
                    for img_file in images_to_delete:
                        if img_file:
                            try:
                                file_path = os.path.join(image_folder, img_file)
                                if os.path.exists(file_path):
                                    os.remove(file_path)
                                    logger.info(
                                        f"File gambar terkait produk {product_id} dihapus: {img_file}"
                                    )
                                else:
                                    logger.warning(
                                        f"File gambar tidak ditemukan untuk produk {product_id} yang dihapus: {img_file}"
                                    )
                            except OSError as e:
                                logger.error(
                                    f"Kesalahan saat menghapus file gambar {img_file} untuk produk {product_id}: {e}",
                                    exc_info=True
                                )

                return {'success': True, 'message': 'Produk berhasil dihapus.'}

            logger.warning(f"ID Produk {product_id} tidak ditemukan untuk dihapus.")
            return {'success': False, 'message': 'Produk tidak ditemukan.'}

        except Exception as e:
            if conn.is_connected():
                conn.rollback()
            logger.error(f"Kesalahan saat menghapus ID produk {product_id}: {e}", exc_info=True)
            return {'success': False, 'message': 'Gagal menghapus produk.'}

        finally:
            cursor.close()
            conn.close()
            logger.debug(f"Koneksi database ditutup untuk delete_product {product_id}")


product_service = ProductService()