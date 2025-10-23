from flask import render_template, request, session, redirect, url_for, flash, jsonify, abort
from app.core.db import get_db_connection, get_content
from app.utils.route_decorators import login_required
from app.services.users.user_service import user_service
from . import user_bp


@user_bp.route('/profile')
@login_required
def user_profile():
    user_id = session['user_id']
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    orders = conn.execute('SELECT * FROM orders WHERE user_id = ? ORDER BY order_date DESC', (user_id,)).fetchall()
    conn.close()
    return render_template('user/user_profile.html', user=user, orders=orders, content=get_content())


@user_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user_id = session['user_id']
    if request.method == 'POST':
        action = request.form.get('form_action')
        result = {}

        if action == 'update_info':
            result = user_service.update_user_info(
                user_id, request.form['username'], request.form['email']
            )
            if result.get('success'):
                session['username'] = request.form['username']
                result['data'] = {'username': request.form['username'], 'email': request.form['email']}

        elif action == 'change_password':
            result = user_service.change_user_password(
                user_id, request.form['current_password'], request.form['new_password']
            )

        elif action == 'update_address':
            address_data = {
                'phone': request.form['phone'],
                'address1': request.form['address_line_1'],
                'address2': request.form.get('address_line_2', ''),
                'city': request.form['city'],
                'province': request.form['province'],
                'postal_code': request.form['postal_code']
            }
            result = user_service.update_user_address(user_id, address_data)
            if result.get('success'):
                result['data'] = request.form

        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if is_ajax:
            return jsonify(result)

        flash(result.get('message', 'Terjadi kesalahan.'), 'success' if result.get('success') else 'danger')
        return redirect(url_for('user.edit_profile'))

    user = user_service.get_user_by_id(user_id)
    return render_template('user/profile_editor.html', user=user, content=get_content())

@user_bp.route('/order/track/<int:order_id>')
@login_required
def track_order(order_id):
    user_id = session['user_id']
    conn = get_db_connection()
    try:
        order = conn.execute('SELECT * FROM orders WHERE id = ? AND user_id = ?', (order_id, user_id)).fetchone()
        if not order:
            abort(404, description="Pesanan tidak ditemukan atau Anda tidak memiliki akses.")

        items = conn.execute("""
            SELECT oi.*, p.name
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = ?
        """, (order_id,)).fetchall()

        history_list = conn.execute("""
            SELECT * FROM order_status_history
            WHERE order_id = ? ORDER BY timestamp ASC
        """, (order_id,)).fetchall()

    finally:
        conn.close()

    return render_template(
        'user/order_tracking.html',
        order=order,
        items=items,
        history_list=history_list,
        content=get_content()
    )