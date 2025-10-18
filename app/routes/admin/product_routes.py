import os
import json
import uuid
from flask import render_template, request, redirect, url_for, flash, current_app
from PIL import Image

from . import admin_bp
from database.db_config import get_db_connection, get_content
from utils.route_decorators import admin_required

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_compressed_image(file_storage):
    try:
        filename_base = str(uuid.uuid4())
        filename = f"{filename_base}.webp"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        image = Image.open(file_storage.stream)
        if hasattr(image, '_getexif') and image._getexif() is not None:
            exif = dict(image._getexif().items())
            orientation_key = 274
            if orientation_key in exif:
                orientation = exif[orientation_key]
                if orientation == 3: image = image.rotate(180, expand=True)
                elif orientation == 6: image = image.rotate(270, expand=True)
                elif orientation == 8: image = image.rotate(90, expand=True)
        image.thumbnail((1080, 1080))
        image.save(filepath, 'WEBP', quality=85, optimize=True)
        return filename
    except Exception as e:
        print(f"Error processing image: {e}")
        return None

@admin_bp.route('/products', methods=['GET', 'POST'])
@admin_required
def admin_products():
    conn = get_db_connection()
    if request.method == 'POST':
        action = request.form.get('bulk_action')
        selected_ids = request.form.getlist('product_ids')

        if action and selected_ids:
            if action == 'delete':
                placeholders = ', '.join(['?'] * len(selected_ids))
                conn.execute(f'DELETE FROM products WHERE id IN ({placeholders})', selected_ids)
                conn.commit()
                flash(f'{len(selected_ids)} produk berhasil dihapus.', 'success')
            elif action == 'set_category':
                category_id = request.form.get('bulk_category_id')
                if category_id:
                    placeholders = ', '.join(['?'] * len(selected_ids))
                    conn.execute(f'UPDATE products SET category_id = ? WHERE id IN ({placeholders})', [category_id] + selected_ids)
                    conn.commit()
                    flash(f'Kategori untuk {len(selected_ids)} produk berhasil diubah.', 'success')
            return redirect(url_for('admin.admin_products'))

        name, price, description = request.form['name'], request.form['price'], request.form['description']
        category_id, sizes, colors, stock = request.form['category_id'], request.form['sizes'], request.form['colors'], request.form['stock']
        discount_price = request.form.get('discount_price') or None
        
        images = request.files.getlist("images")
        main_image_identifier = request.form.get('main_image')

        if not images or all(f.filename == '' for f in images):
            flash('Anda harus mengunggah setidaknya satu gambar.', 'danger')
        elif not main_image_identifier:
            flash('Anda harus memilih satu gambar sebagai gambar utama.', 'danger')
        else:
            saved_filenames = {img.filename: save_compressed_image(img) for img in images if img and allowed_file(img.filename)}
            saved_filenames = {k: v for k, v in saved_filenames.items() if v}
            main_image_url = saved_filenames.get(main_image_identifier)
            additional_image_urls = [fname for orig, fname in saved_filenames.items() if orig != main_image_identifier]
            
            if not main_image_url:
                flash('Gambar utama yang dipilih tidak valid atau gagal diproses.', 'danger')
            else:
                conn.execute(
                    'INSERT INTO products (name, price, discount_price, description, category_id, sizes, colors, image_url, additional_image_urls, stock) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                    (name, price, discount_price, description, category_id, sizes, colors, main_image_url, json.dumps(additional_image_urls), stock)
                )
                conn.commit()
                flash('Produk berhasil ditambahkan!', 'success')
        
        return redirect(url_for('admin.admin_products'))
    
    products_raw = conn.execute('SELECT p.*, c.name as category_name FROM products p LEFT JOIN categories c ON p.category_id = c.id ORDER BY p.id DESC').fetchall()
    categories = conn.execute('SELECT * FROM categories ORDER BY name ASC').fetchall()
    conn.close()
    return render_template('admin/manage_products.html', products=products_raw, categories=categories, content=get_content())

@admin_bp.route('/edit_product/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(id):
    conn = get_db_connection()
    if request.method == 'POST':
        name, price, description = request.form['name'], request.form['price'], request.form['description']
        category_id, sizes, colors, stock = request.form['category_id'], request.form['sizes'], request.form['colors'], request.form['stock']
        discount_price = request.form.get('discount_price')
        discount_price = float(discount_price) if discount_price else None

        product = conn.execute('SELECT image_url, additional_image_urls FROM products WHERE id = ?', (id,)).fetchone()
        existing_additional_images = json.loads(product['additional_image_urls']) if product['additional_image_urls'] else []
        all_current_images = [product['image_url']] + existing_additional_images
        images_to_delete = request.form.getlist('delete_image')
        remaining_images = [img for img in all_current_images if img not in images_to_delete]

        new_images = request.files.getlist("new_images")
        newly_saved_filenames = [save_compressed_image(img) for img in new_images if img and allowed_file(img.filename)]
        newly_saved_filenames = [name for name in newly_saved_filenames if name]
        
        final_image_pool = remaining_images + newly_saved_filenames
        new_main_image = request.form.get('main_image')
        
        if not final_image_pool:
            flash('Produk harus memiliki setidaknya satu gambar.', 'danger')
            return redirect(url_for('admin.admin_edit_product', id=id))

        final_main_image = new_main_image if new_main_image in final_image_pool else final_image_pool[0]
        final_additional_images = [img for img in final_image_pool if img != final_main_image]

        conn.execute(
            'UPDATE products SET name = ?, price = ?, discount_price = ?, description = ?, category_id = ?, sizes = ?, colors = ?, stock = ?, image_url = ?, additional_image_urls = ? WHERE id = ?', 
            (name, price, discount_price, description, category_id, sizes, colors, stock, final_main_image, json.dumps(final_additional_images), id)
        )
        conn.commit()
        
        for img_file in images_to_delete:
            try: os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], img_file))
            except OSError as e: print(f"Error saat menghapus file {img_file}: {e}")

        flash('Produk berhasil diperbarui!', 'success')
        return redirect(url_for('admin.admin_products'))

    product_row = conn.execute('SELECT * FROM products WHERE id = ?', (id,)).fetchone()
    if not product_row:
        flash('Produk tidak ditemukan.', 'danger')
        return redirect(url_for('admin.admin_products'))
    
    product = dict(product_row)
    additional_images = json.loads(product['additional_image_urls']) if product['additional_image_urls'] else []
    categories = conn.execute('SELECT * FROM categories ORDER BY name ASC').fetchall()
    conn.close()
    return render_template('admin/product_editor.html', product=product, additional_images=additional_images, categories=categories, content=get_content())

@admin_bp.route('/delete_product/<int:id>')
@admin_required
def delete_product(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM products WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Produk berhasil dihapus!', 'success')
    return redirect(url_for('admin.admin_products'))

@admin_bp.route('/categories', methods=['GET', 'POST'])
@admin_required
def admin_categories():
    conn = get_db_connection()
    if request.method == 'POST':
        action = request.form.get('action')
        name = request.form.get('name')
        category_id = request.form.get('id')

        if action == 'add' and name:
            try:
                conn.execute('INSERT INTO categories (name) VALUES (?)', (name,))
                conn.commit()
                flash(f'Kategori "{name}" berhasil ditambahkan.', 'success')
            except conn.IntegrityError:
                flash(f'Kategori "{name}" sudah ada.', 'danger')
        elif action == 'edit' and name and category_id:
            conn.execute('UPDATE categories SET name = ? WHERE id = ?', (name, category_id))
            conn.commit()
            flash('Kategori berhasil diperbarui.', 'success')
        
        return redirect(url_for('admin.admin_categories'))
    
    categories = conn.execute('SELECT * FROM categories ORDER BY name ASC').fetchall()
    conn.close()
    return render_template('admin/manage_categories.html', categories=categories, content=get_content())

@admin_bp.route('/delete_category/<int:id>')
@admin_required
def delete_category(id):
    conn = get_db_connection()
    conn.execute('UPDATE products SET category_id = NULL WHERE category_id = ?', (id,))
    conn.execute('DELETE FROM categories WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Kategori berhasil dihapus.', 'success')
    return redirect(url_for('admin.admin_categories'))