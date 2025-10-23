import json
import uuid
from flask import render_template, request, session, redirect, url_for, flash
from db.db_config import get_db_connection, get_content
from utils.route_decorators import login_required
from services.users.user_service import user_service
from services.orders.order_service import order_service
from services.orders.cart_service import cart_service
from services.orders.stock_service import stock_service

from . import purchase_bp


@purchase_bp.route('/cart')
def cart_page():
    return render_template('purchase/cart.html', content=get_content())


@purchase_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    user_id = session.get('user_id')
    user = user_service.get_user_by_id(user_id) if user_id else None

    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    session_id = session['session_id']

    if request.method == 'POST':
        cart_data = None
        if not user_id:
            cart_json = request.form.get('cart_data')
            if not cart_json or cart_json == '{}':
                flash("Keranjang Anda kosong.", 'danger')
                return redirect(url_for('purchase.cart_page'))
            cart_data = json.loads(cart_json)

        if user_id:
            if not user:
                user = user_service.get_user_by_id(user_id)
            shipping_details = {
                'name': user.get('username'), 'phone': user.get('phone'),
                'address1': user.get('address_line_1'), 'address2': user.get('address_line_2', ''),
                'city': user.get('city'), 'province': user.get('province'),
                'postal_code': user.get('postal_code')
            }
            if not all([shipping_details['phone'], shipping_details['address1'], shipping_details['city']]):
                flash('Alamat pengiriman Anda belum lengkap.', 'danger')
                return redirect(url_for('purchase.edit_address'))
        else:
            shipping_details = {
                'name': request.form['full_name'], 'phone': request.form['phone'],
                'address1': request.form['address_line_1'], 'address2': request.form.get('address_line_2', ''),
                'city': request.form['city'], 'province': request.form['province'],
                'postal_code': request.form['postal_code']
            }
            email_for_order = request.form.get('email')
            if not email_for_order:
                flash('Email wajib diisi untuk checkout.', 'danger')
                return redirect(url_for('purchase.checkout'))

            conn = get_db_connection()
            if conn.execute('SELECT id FROM users WHERE email = ?', (email_for_order,)).fetchone():
                conn.close()
                flash('Email sudah terdaftar. Silakan login.', 'danger')
                return redirect(url_for('auth.login', next=url_for('purchase.checkout')))
            conn.close()
            session['guest_order_details'] = {'email': email_for_order, **shipping_details}

        payment_method = request.form['payment_method']
        voucher_code = request.form.get('voucher_code') or None
        shipping_cost = request.form.get('shipping_cost', 0, type=float)

        result = order_service.create_order(
            user_id, session_id, cart_data, shipping_details,
            payment_method, voucher_code, shipping_cost
        )

        if result['success']:
            order_id = result['order_id']
            if not user_id:
                session['guest_order_id'] = order_id

            if payment_method == 'COD':
                flash(f"Pesanan #{order_id} berhasil dibuat!", 'success')
                return redirect(url_for('purchase.order_success'))
            else:
                return redirect(url_for('purchase.payment_page', order_id=order_id))
        else:
            flash(result['message'], 'danger')
            return redirect(url_for('purchase.cart_page'))

    if user_id:
        cart_details = cart_service.get_cart_details(user_id)
        if not cart_details['items']:
            flash("Keranjang Anda kosong.", "warning")
            return redirect(url_for('purchase.cart_page'))

        hold_result = stock_service.hold_stock_for_checkout(user_id, None, cart_details['items'])
        if not hold_result['success']:
            flash(hold_result['message'], 'danger')
            return redirect(url_for('purchase.cart_page'))

        return render_template(
            'purchase/checkout_page.html',
            user=user,
            content=get_content(),
            stock_hold_expires=hold_result.get('expires_at')
        )
    else:
        return render_template(
            'purchase/checkout_page.html',
            user=None,
            content=get_content(),
            stock_hold_expires=None
        )


@purchase_bp.route('/checkout/edit_address', methods=['GET', 'POST'])
@login_required
def edit_address():
    user_id = session['user_id']
    if request.method == 'POST':
        address_data = {
            'phone': request.form['phone'],
            'address1': request.form['address_line_1'],
            'address2': request.form.get('address_line_2', ''),
            'city': request.form['city'],
            'province': request.form['province'],
            'postal_code': request.form['postal_code']
        }
        user_service.update_user_address(user_id, address_data)
        flash('Alamat berhasil diperbarui.', 'success')
        return redirect(url_for('purchase.checkout'))

    user = user_service.get_user_by_id(user_id)
    return render_template('purchase/edit_address_page.html', user=user, content=get_content())