import json
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from database.db_config import get_db_connection, get_content
from utils.route_decorators import login_required
from services.user_service import user_service
from services.order_service import order_service

user_bp = Blueprint('user', __name__)

@user_bp.route('/profile')
@login_required
def user_profile():
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    orders = conn.execute('SELECT * FROM orders WHERE user_id = ? ORDER BY order_date DESC', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('user/user_profile.html', user=user, orders=orders, content=get_content())

@user_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user_id = session['user_id']
    if request.method == 'POST':
        if 'update_info' in request.form:
            result = user_service.update_user_info(
                user_id, request.form['username'], request.form['email']
            )
            if result['success']:
                session['username'] = request.form['username']
            flash(result['message'], 'success' if result['success'] else 'danger')
        
        elif 'change_password' in request.form:
            result = user_service.change_user_password(
                user_id, request.form['current_password'], request.form['new_password']
            )
            flash(result['message'], 'success' if result['success'] else 'danger')

        elif 'update_address' in request.form:
            address_data = {
                'phone': request.form['phone'], 'address1': request.form['address_line_1'],
                'address2': request.form.get('address_line_2', ''), 'city': request.form['city'],
                'province': request.form['province'], 'postal_code': request.form['postal_code']
            }
            result = user_service.update_user_address(user_id, address_data)
            flash(result['message'], 'success')
        
        return redirect(url_for('user.edit_profile'))
    
    user = user_service.get_user_by_id(user_id)
    return render_template('user/profile_editor.html', user=user, content=get_content())


@user_bp.route('/cart')
def cart_page():
    return render_template('public/cart.html', content=get_content())

@user_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    user = None
    if 'user_id' in session:
        user = user_service.get_user_by_id(session['user_id'])

    if request.method == 'POST':
        cart_json = request.form.get('cart_data')
        if not cart_json:
            flash("Data keranjang tidak ditemukan.", 'danger')
            return redirect(url_for('user.cart_page'))
        
        cart_data = json.loads(cart_json)
        shipping_details = {
            'name': request.form['full_name'], 'phone': request.form['phone'],
            'address1': request.form['address_line_1'], 'address2': request.form.get('address_line_2', ''),
            'city': request.form['city'], 'province': request.form['province'],
            'postal_code': request.form['postal_code']
        }
        payment_method = request.form['payment_method']
        user_id_for_order = session.get('user_id')

        if not user_id_for_order:
            email_for_order = request.form.get('email')
            if not email_for_order:
                flash('Email wajib diisi untuk checkout.', 'danger')
                return redirect(url_for('user.checkout'))
            
            conn = get_db_connection()
            existing_user = conn.execute('SELECT id FROM users WHERE email = ?', (email_for_order,)).fetchone()
            conn.close()
            if existing_user:
                flash('Email sudah terdaftar. Silakan login untuk melanjutkan.', 'danger')
                return redirect(url_for('auth.login', next=url_for('user.checkout')))

        save_address = 'save_address' in request.form and user_id_for_order is not None
        result = order_service.create_order(user_id_for_order, cart_data, shipping_details, payment_method, save_address)

        if result['success']:
            if not user_id_for_order:
                session['guest_order_id'] = result['order_id']
                session['guest_order_details'] = {
                    'email': request.form.get('email'),
                    **shipping_details
                }
            flash(f"Pesanan #{result['order_id']} berhasil dibuat!", 'success')
            return redirect(url_for('user.order_success'))
        else:
            flash(result['message'], 'danger')
            return redirect(url_for('user.cart_page'))

    return render_template('user/checkout_page.html', user=user, content=get_content())


@user_bp.route('/order_success')
def order_success():
    guest_order_details = session.pop('guest_order_details', None)
    guest_order_id = session.pop('guest_order_id', None)
    return render_template('user/success_page.html', content=get_content(), 
                           guest_order_details=guest_order_details, 
                           guest_order_id=guest_order_id)

@user_bp.route('/order/cancel/<int:order_id>', methods=['POST'])
@login_required
def cancel_order(order_id):
    result = order_service.cancel_user_order(order_id, session['user_id'])
    flash(result['message'], 'success' if result['success'] else 'danger')
    return redirect(url_for('user.user_profile'))