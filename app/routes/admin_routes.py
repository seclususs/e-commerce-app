import os
import json
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from PIL import Image
from database.db_config import get_db_connection, get_content
from utils.route_decorators import admin_required
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__)

def allowed_file(filename):
    """Fungsi helper untuk memeriksa ekstensi file yang diizinkan."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_compressed_image(file_storage):
    """
    Mengambil objek FileStorage, mengompresnya, dan menyimpannya sebagai WebP.
    Mengembalikan nama file yang disimpan.
    """
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


@admin_bp.route('/dashboard')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    product_count = conn.execute('SELECT COUNT(id) FROM products').fetchone()[0]
    order_count = conn.execute('SELECT COUNT(id) FROM orders').fetchone()[0]
    total_sales = conn.execute("SELECT SUM(total_amount) FROM orders WHERE status != 'Cancelled'").fetchone()[0]
    recent_orders_raw = conn.execute('SELECT o.*, u.username as customer_name FROM orders o LEFT JOIN users u ON o.user_id = u.id ORDER BY o.order_date DESC LIMIT 5').fetchall()
    
    # Logika untuk mengambil data penjualan 7 hari terakhir
    today = datetime.now()
    seven_days_ago = today - timedelta(days=6)
    
    # Kueri untuk mengambil penjualan harian
    sales_data_raw = conn.execute("""
        SELECT date(order_date) as sale_date, SUM(total_amount) as daily_total
        FROM orders
        WHERE date(order_date) >= ? AND status != 'Cancelled'
        GROUP BY sale_date
        ORDER BY sale_date ASC
    """, (seven_days_ago.strftime('%Y-%m-%d'),)).fetchall()

    conn.close()

    # Memproses data untuk chart
    sales_by_date = {row['sale_date']: row['daily_total'] for row in sales_data_raw}
    chart_labels = []
    chart_data = []
    for i in range(7):
        current_date = seven_days_ago + timedelta(days=i)
        date_str = current_date.strftime('%Y-%m-%d')
        chart_labels.append(current_date.strftime('%d %b')) # Format: 16 Okt
        chart_data.append(sales_by_date.get(date_str, 0))

    stats = { 'product_count': product_count, 'order_count': order_count, 'total_sales': total_sales or 0 }
    
    return render_template(
        'admin/dashboard.html', 
        stats=stats, 
        recent_orders=recent_orders_raw, 
        content=get_content(),
        chart_labels=chart_labels, # Melewatkan data chart ke template
        chart_data=chart_data      # Melewatkan data chart ke template
    )


@admin_bp.route('/products', methods=['GET', 'POST'])
@admin_required
def admin_products():
    conn = get_db_connection()
    if request.method == 'POST':
        name, price, description = request.form['name'], request.form['price'], request.form['description']
        category, sizes, colors, stock = request.form['category'], request.form['sizes'], request.form['colors'], request.form['stock']
        
        images = request.files.getlist("images")
        main_image_identifier = request.form.get('main_image')

        if not images or all(f.filename == '' for f in images):
            flash('Anda harus mengunggah setidaknya satu gambar.', 'danger')
            return redirect(url_for('admin.admin_products'))
        if not main_image_identifier:
            flash('Anda harus memilih satu gambar sebagai gambar utama.', 'danger')
            return redirect(url_for('admin.admin_products'))

        saved_filenames = {img.filename: save_compressed_image(img) for img in images if img and allowed_file(img.filename)}
        saved_filenames = {k: v for k, v in saved_filenames.items() if v}
        
        main_image_url = saved_filenames.get(main_image_identifier)
        additional_image_urls = [fname for orig, fname in saved_filenames.items() if orig != main_image_identifier]
        
        if not main_image_url:
            flash('Gambar utama yang dipilih tidak valid atau gagal diproses.', 'danger')
            return redirect(url_for('admin.admin_products'))

        conn.execute(
            'INSERT INTO products (name, price, description, category, sizes, colors, image_url, additional_image_urls, stock) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', 
            (name, price, description, category, sizes, colors, main_image_url, json.dumps(additional_image_urls), stock)
        )
        conn.commit()
        flash('Produk berhasil ditambahkan!', 'success')
        return redirect(url_for('admin.admin_products'))
    
    products = conn.execute('SELECT * FROM products ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('admin/manage_products.html', products=products, content=get_content())

@admin_bp.route('/edit_product/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(id):
    conn = get_db_connection()
    product_row = conn.execute('SELECT * FROM products WHERE id = ?', (id,)).fetchone()
    if not product_row:
        flash('Produk tidak ditemukan.', 'danger')
        return redirect(url_for('admin.admin_products'))
        
    product = dict(product_row)
    existing_additional_images = json.loads(product['additional_image_urls']) if product['additional_image_urls'] else []

    if request.method == 'POST':
        name, price, description = request.form['name'], request.form['price'], request.form['description']
        category, sizes, colors, stock = request.form['category'], request.form['sizes'], request.form['colors'], request.form['stock']

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
            'UPDATE products SET name = ?, price = ?, description = ?, category = ?, sizes = ?, colors = ?, stock = ?, image_url = ?, additional_image_urls = ? WHERE id = ?', 
            (name, price, description, category, sizes, colors, stock, final_main_image, json.dumps(final_additional_images), id)
        )
        conn.commit()
        
        for img_file in images_to_delete:
            try: os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], img_file))
            except OSError as e: print(f"Error saat menghapus file {img_file}: {e}")

        flash('Produk berhasil diperbarui!', 'success')
        return redirect(url_for('admin.admin_products'))

    conn.close()
    return render_template('admin/product_editor.html', product=product, additional_images=existing_additional_images, content=get_content())

@admin_bp.route('/delete_product/<int:id>')
@admin_required
def delete_product(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM products WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Produk berhasil dihapus!', 'success')
    return redirect(url_for('admin.admin_products'))

@admin_bp.route('/orders')
@admin_required
def admin_orders():
    conn = get_db_connection()
    orders = conn.execute('SELECT o.*, u.username as customer_name FROM orders o LEFT JOIN users u ON o.user_id = u.id ORDER BY o.order_date DESC').fetchall()
    conn.close()
    return render_template('admin/manage_orders.html', orders=orders, content=get_content())

@admin_bp.route('/order/<int:id>')
@admin_required
def admin_order_detail(id):
    conn = get_db_connection()
    order = conn.execute('SELECT o.*, u.username as customer_name, u.email FROM orders o LEFT JOIN users u ON o.user_id = u.id WHERE o.id = ?', (id,)).fetchone()
    items = conn.execute('SELECT p.name, oi.quantity, oi.price FROM order_items oi JOIN products p ON oi.product_id = p.id WHERE oi.order_id = ?', (id,)).fetchall()
    conn.close()
    return render_template('admin/view_order.html', order=order, items=items, content=get_content())

@admin_bp.route('/update_order_status/<int:id>', methods=['POST'])
@admin_required
def update_order_status(id):
    status = request.form['status']
    conn = get_db_connection()
    order = conn.execute('SELECT * FROM orders WHERE id = ?', (id,)).fetchone()
    
    if status == 'Cancelled' and order['status'] != 'Cancelled':
        order_items = conn.execute('SELECT * FROM order_items WHERE order_id = ?', (id,)).fetchall()
        for item in order_items:
            conn.execute('UPDATE products SET stock = stock + ? WHERE id = ?', (item['quantity'], item['product_id']))
        flash(f'Stok untuk pesanan #{id} telah dikembalikan.', 'info')

    conn.execute('UPDATE orders SET status = ? WHERE id = ?', (status, id))
    conn.commit()
    conn.close()
    flash(f'Status pesanan #{id} berhasil diperbarui!', 'success')
    return redirect(url_for('admin.admin_order_detail', id=id))

@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    conn = get_db_connection()
    if request.method == 'POST':
        for key, value in request.form.items():
            conn.execute('UPDATE content SET value = ? WHERE key = ?', (value, key))
        conn.commit()
        flash('Pengaturan konten berhasil diperbarui!', 'success')
        return redirect(url_for('admin.admin_settings'))
    content_data = get_content()
    conn.close()
    return render_template('admin/site_settings.html', content=content_data)