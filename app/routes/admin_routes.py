import os
import json
import uuid
import csv
import random
from io import StringIO
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, Response
from werkzeug.utils import secure_filename
from PIL import Image
from database.db_config import get_db_connection, get_content
from utils.route_decorators import admin_required
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__)

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

def get_date_range(period_str):
    """Mendapatkan rentang tanggal berdasarkan string periode."""
    today = datetime.now()
    if period_str == 'last_30_days':
        start_date = today - timedelta(days=29)
        end_date = today
    elif period_str == 'this_month':
        start_date = today.replace(day=1)
        end_date = today
    else: # Default ke 7 hari terakhir jika tidak ada atau tidak valid
        start_date = today - timedelta(days=6)
        end_date = today
    return start_date.strftime('%Y-%m-%d 00:00:00'), end_date.strftime('%Y-%m-%d 23:59:59')

@admin_bp.route('/dashboard')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    
    # Logika rentang waktu
    period = request.args.get('period', 'last_7_days') # Default 7 hari
    custom_start = request.args.get('custom_start')
    custom_end = request.args.get('custom_end')

    if custom_start and custom_end:
        start_date_str = f"{custom_start} 00:00:00"
        end_date_str = f"{custom_end} 23:59:59"
        period = 'custom'
    else:
        start_date_str, end_date_str = get_date_range(period)

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d %H:%M:%S')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S')

    # Query stats dengan rentang waktu
    total_sales = conn.execute("SELECT SUM(total_amount) FROM orders WHERE status != 'Cancelled' AND order_date BETWEEN ? AND ?", (start_date_str, end_date_str)).fetchone()[0]
    order_count = conn.execute("SELECT COUNT(id) FROM orders WHERE order_date BETWEEN ? AND ?", (start_date_str, end_date_str)).fetchone()[0]
    new_user_count = conn.execute("SELECT COUNT(id) FROM users WHERE created_at BETWEEN ? AND ?", (start_date_str, end_date_str)).fetchone()[0]
    product_count = conn.execute('SELECT COUNT(id) FROM products').fetchone()[0] # Total produk tidak terikat waktu

    # Query kartu baru
    top_products = conn.execute("""
        SELECT p.name, SUM(oi.quantity) as total_sold
        FROM order_items oi JOIN products p ON oi.product_id = p.id JOIN orders o ON oi.order_id = o.id
        WHERE o.status != 'Cancelled' AND o.order_date BETWEEN ? AND ?
        GROUP BY p.id ORDER BY total_sold DESC LIMIT 5
    """, (start_date_str, end_date_str)).fetchall()
    
    # Menambahkan kolom 'id' ke dalam query
    low_stock_products = conn.execute("SELECT id, name, stock FROM products WHERE stock > 0 AND stock <= 5 ORDER BY stock ASC LIMIT 5").fetchall()

    # Logika Chart dengan rentang waktu dinamis
    sales_data_raw = conn.execute("""
        SELECT date(order_date) as sale_date, SUM(total_amount) as daily_total
        FROM orders WHERE status != 'Cancelled' AND order_date BETWEEN ? AND ?
        GROUP BY sale_date ORDER BY sale_date ASC
    """, (start_date_str, end_date_str)).fetchall()

    sales_by_date = {row['sale_date']: row['daily_total'] for row in sales_data_raw}
    chart_labels, chart_data = [], []
    delta = end_date.date() - start_date.date()
    for i in range(delta.days + 1):
        current_date = start_date.date() + timedelta(days=i)
        date_str = current_date.strftime('%Y-%m-%d')
        chart_labels.append(current_date.strftime('%d %b'))
        chart_data.append(sales_by_date.get(date_str, 0))

    conn.close()

    stats = {
        'product_count': product_count,
        'order_count': order_count,
        'total_sales': total_sales or 0,
        'new_user_count': new_user_count,
        'top_products': top_products,
        'low_stock_products': low_stock_products
    }
    
    return render_template(
        'admin/dashboard.html', stats=stats, content=get_content(),
        chart_labels=chart_labels, chart_data=chart_data,
        selected_period=period, custom_start=custom_start, custom_end=custom_end
    )

@admin_bp.route('/products', methods=['GET', 'POST'])
@admin_required
def admin_products():
    conn = get_db_connection()
    if request.method == 'POST':
        # Logika untuk aksi massal
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
            # Anda bisa menambahkan aksi diskon massal di sini
            return redirect(url_for('admin.admin_products'))

        # Logika tambah produk
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


@admin_bp.route('/orders')
@admin_required
def admin_orders():
    conn = get_db_connection()
    
    # Logika filter dan pencarian
    status_filter = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    search_query = request.args.get('search')

    query = 'SELECT o.*, u.username as customer_name FROM orders o LEFT JOIN users u ON o.user_id = u.id WHERE 1=1'
    params = []

    if status_filter:
        query += ' AND o.status = ?'
        params.append(status_filter)
    if start_date:
        query += ' AND date(o.order_date) >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND date(o.order_date) <= ?'
        params.append(end_date)
    if search_query:
        query += " AND (o.id LIKE ? OR u.username LIKE ? OR o.shipping_name LIKE ?)"
        params.extend([f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'])

    query += ' ORDER BY o.order_date DESC'
    
    orders = conn.execute(query, params).fetchall()
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

@admin_bp.route('/order/invoice/<int:id>')
@admin_required
def admin_order_invoice(id):
    conn = get_db_connection()
    order = conn.execute('SELECT o.*, u.email FROM orders o LEFT JOIN users u ON o.user_id = u.id WHERE o.id = ?', (id,)).fetchone()
    items = conn.execute('SELECT p.name, oi.quantity, oi.price FROM order_items oi JOIN products p ON oi.product_id = p.id WHERE oi.order_id = ?', (id,)).fetchall()
    conn.close()
    if not order:
        return "Pesanan tidak ditemukan", 404
    return render_template('admin/invoice.html', order=order, items=items)

@admin_bp.route('/update_order_status/<int:id>', methods=['POST'])
@admin_required
def update_order_status(id):
    conn = get_db_connection()
    
    status = request.form.get('status')
    tracking_number = request.form.get('tracking_number')

    # Ambil status order saat ini
    order = conn.execute('SELECT status, tracking_number FROM orders WHERE id = ?', (id,)).fetchone()

    # Logika untuk nomor resi otomatis
    if status == 'Shipped' and not order['tracking_number']:
        tracking_number = f"HT-{random.randint(10000000, 99999999)}"
        flash(f'Nomor resi otomatis digenerate: {tracking_number}', 'info')
    
    # Logika untuk pengembalian stok
    if status == 'Cancelled' and order['status'] != 'Cancelled':
        order_items = conn.execute('SELECT * FROM order_items WHERE order_id = ?', (id,)).fetchall()
        for item in order_items:
            conn.execute('UPDATE products SET stock = stock + ? WHERE id = ?', (item['quantity'], item['product_id']))
        flash(f'Stok untuk pesanan #{id} telah dikembalikan.', 'info')

    # Update status dan nomor resi
    conn.execute('UPDATE orders SET status = ?, tracking_number = ? WHERE id = ?', (status, tracking_number, id))
    conn.commit()
    conn.close()

    flash(f'Pesanan #{id} berhasil diperbarui!', 'success')
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

@admin_bp.route('/reports')
@admin_required
def admin_reports():
    conn = get_db_connection()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    date_filter = " WHERE 1=1 "
    params = []
    if start_date:
        date_filter += " AND o.order_date >= ? "
        params.append(start_date + ' 00:00:00')
    if end_date:
        date_filter += " AND o.order_date <= ? "
        params.append(end_date + ' 23:59:59')
    
    sales_query = f"""SELECT 
                        COALESCE(SUM(o.total_amount), 0) as total_revenue, 
                        COUNT(o.id) as total_orders, 
                        COALESCE(SUM(oi.quantity), 0) as total_items_sold
                     FROM orders o
                     LEFT JOIN order_items oi ON o.id = oi.order_id
                     {date_filter.replace('o.order_date', 'o.order_date')} AND o.status != 'Cancelled'"""
    
    sales_report = conn.execute(sales_query, params).fetchone()

    top_selling_products = conn.execute(f"""
        SELECT p.name, SUM(oi.quantity) as total_sold FROM products p
        JOIN order_items oi ON p.id = oi.product_id
        JOIN orders o ON oi.order_id = o.id
        {date_filter} AND o.status != 'Cancelled'
        GROUP BY p.id ORDER BY total_sold DESC LIMIT 10
    """, params).fetchall()

    most_viewed_products = conn.execute("SELECT name, popularity FROM products ORDER BY popularity DESC LIMIT 10").fetchall()

    top_spenders = conn.execute(f"""
        SELECT u.username, u.email, SUM(o.total_amount) as total_spent FROM users u
        JOIN orders o ON u.id = o.user_id
        {date_filter} AND o.status != 'Cancelled'
        GROUP BY u.id ORDER BY total_spent DESC LIMIT 10
    """, params).fetchall()

    conn.close()

    reports_data = {
        'sales': dict(sales_report),
        'products': {
            'top_selling': top_selling_products,
            'most_viewed': most_viewed_products
        },
        'customers': {
            'top_spenders': top_spenders
        }
    }
    return render_template('admin/reports.html', reports=reports_data, content=get_content())

@admin_bp.route('/export/<report_name>')
@admin_required
def export_report(report_name):
    conn = get_db_connection()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    si = StringIO()
    cw = csv.writer(si)

    date_filter = " WHERE 1=1 "
    params = []
    if start_date:
        date_filter += " AND o.order_date >= ? "
        params.append(start_date)
    if end_date:
        date_filter += " AND o.order_date <= ? "
        params.append(end_date)

    if report_name == 'sales':
        headers = ['ID Pesanan', 'Tanggal', 'Nama Pelanggan', 'Total', 'Status']
        query = f"SELECT o.id, o.order_date, o.shipping_name, o.total_amount, o.status FROM orders o {date_filter} AND o.status != 'Cancelled' ORDER BY o.order_date DESC"
        data = conn.execute(query, params).fetchall()
    elif report_name == 'products':
        headers = ['ID Produk', 'Nama Produk', 'Terjual', 'Dilihat']
        query = f"""
            SELECT p.id, p.name, COALESCE(SUM(oi.quantity), 0) as total_sold, p.popularity
            FROM products p
            LEFT JOIN order_items oi ON p.id = oi.product_id
            LEFT JOIN orders o ON oi.order_id = o.id AND (o.status != 'Cancelled' {date_filter.replace('WHERE 1=1', '')})
            GROUP BY p.id ORDER BY total_sold DESC
        """
        data = conn.execute(query, params).fetchall()
    elif report_name == 'customers':
        headers = ['ID Pelanggan', 'Username', 'Email', 'Total Belanja']
        query = f"""
            SELECT u.id, u.username, u.email, SUM(o.total_amount) as total_spent FROM users u
            JOIN orders o ON u.id = o.user_id
            {date_filter} AND o.status != 'Cancelled'
            GROUP BY u.id ORDER BY total_spent DESC
        """
        data = conn.execute(query, params).fetchall()
    else:
        return "Laporan tidak valid", 404

    cw.writerow(headers)
    for row in data:
        cw.writerow(row)
    
    conn.close()
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={report_name}_report_{datetime.now().strftime('%Y%m%d')}.csv"}
    )