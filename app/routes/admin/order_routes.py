import random
from flask import render_template, request, redirect, url_for, flash

from . import admin_bp
from database.db_config import get_db_connection, get_content
from utils.route_decorators import admin_required

@admin_bp.route('/orders')
@admin_required
def admin_orders():
    conn = get_db_connection()
    
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
    return render_template('admin/invoice.html', order=order, items=items, content=get_content())

@admin_bp.route('/update_order_status/<int:id>', methods=['POST'])
@admin_required
def update_order_status(id):
    conn = get_db_connection()
    
    status = request.form.get('status')
    tracking_number = request.form.get('tracking_number')

    order = conn.execute('SELECT status, tracking_number FROM orders WHERE id = ?', (id,)).fetchone()

    if status == 'Shipped' and not order['tracking_number'] and not tracking_number:
        tracking_number = f"HT-{random.randint(10000000, 99999999)}"
        flash(f'Nomor resi otomatis digenerate: {tracking_number}', 'info')
    
    if status == 'Cancelled' and order['status'] != 'Cancelled':
        order_items = conn.execute('SELECT * FROM order_items WHERE order_id = ?', (id,)).fetchall()
        for item in order_items:
            conn.execute('UPDATE products SET stock = stock + ? WHERE id = ?', (item['quantity'], item['product_id']))
        flash(f'Stok untuk pesanan #{id} telah dikembalikan.', 'info')

    conn.execute('UPDATE orders SET status = ?, tracking_number = ? WHERE id = ?', (status, tracking_number, id))
    conn.commit()
    conn.close()

    flash(f'Pesanan #{id} berhasil diperbarui!', 'success')
    return redirect(url_for('admin.admin_order_detail', id=id))