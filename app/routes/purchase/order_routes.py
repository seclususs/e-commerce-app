from flask import render_template, request, session, redirect, url_for, flash, current_app, jsonify
from app.core.db import get_db_connection, get_content
from app.utils.route_decorators import login_required
from app.services.orders.order_service import order_service
from . import purchase_bp


@purchase_bp.route('/order/pay/<int:order_id>')
def payment_page(order_id):
    user_id = session.get('user_id')
    guest_order_id = session.get('guest_order_id')

    conn = get_db_connection()

    if user_id:
        order = conn.execute('SELECT * FROM orders WHERE id = ? AND user_id = ?', (order_id, user_id)).fetchone()
    elif guest_order_id and guest_order_id == order_id:
        order = conn.execute('SELECT * FROM orders WHERE id = ? AND user_id IS NULL', (order_id,)).fetchone()
    else:
        order = None

    if not order or order['payment_method'] == 'COD':
        flash("Pesanan tidak ditemukan atau tidak memerlukan pembayaran online.", "danger")
        return redirect(url_for('product.index'))

    items = conn.execute('SELECT p.name, oi.quantity, oi.price FROM order_items oi JOIN products p ON oi.product_id = p.id WHERE oi.order_id = ?', (order_id,)).fetchall()
    conn.close()

    api_key = current_app.config['SECRET_KEY']

    return render_template(
        'purchase/payment_page.html',
        order=order,
        items=items,
        content=get_content(),
        api_key=api_key
    )


@purchase_bp.route('/order_success')
def order_success():
    guest_order_details = session.pop('guest_order_details', None)
    guest_order_id = session.pop('guest_order_id', None)
    session.pop('session_id', None)

    return render_template(
        'purchase/success_page.html',
        content=get_content(),
        guest_order_details=guest_order_details,
        guest_order_id=guest_order_id
    )


@purchase_bp.route('/order/cancel/<int:order_id>', methods=['POST'])
@login_required
def cancel_order(order_id):
    result = order_service.cancel_user_order(order_id, session['user_id'])

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(result)

    flash(result['message'], 'success' if result['success'] else 'danger')
    return redirect(url_for('user.user_profile'))