import json
from flask import render_template, request, session, redirect, url_for, flash
from database.db_config import get_db_connection, get_content
from utils.route_decorators import login_required
from services.user_service import user_service
from services.order_service import order_service

from . import user_bp

@user_bp.route('/cart')
def cart_page():
    """
    Menampilkan halaman keranjang belanja pengguna.
    """
    return render_template('public/cart.html', content=get_content())

@user_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    """
    Menangani proses checkout, baik untuk pengguna yang sudah login maupun tamu.
    """
    user = None
    if 'user_id' in session:
        user = user_service.get_user_by_id(session['user_id'])

    if request.method == 'POST':
        cart_json = request.form.get('cart_data')
        if not cart_json or cart_json == '{}':
            flash("Keranjang Anda kosong. Silakan tambahkan produk terlebih dahulu.", 'danger')
            return redirect(url_for('user.cart_page'))
        
        cart_data = json.loads(cart_json)
        
        user_id_for_order = session.get('user_id')
        
        # Logika untuk mendapatkan detail pengiriman
        if user_id_for_order:
            if not user:
                 user = user_service.get_user_by_id(user_id_for_order)
            shipping_details = {
                'name': user.get('username'), 'phone': user.get('phone'),
                'address1': user.get('address_line_1'), 'address2': user.get('address_line_2', ''),
                'city': user.get('city'), 'province': user.get('province'),
                'postal_code': user.get('postal_code')
            }
            if not all([shipping_details['phone'], shipping_details['address1'], shipping_details['city']]):
                flash('Alamat pengiriman Anda belum lengkap. Silakan lengkapi terlebih dahulu.', 'danger')
                return redirect(url_for('user.edit_address'))
        else: # Untuk tamu
            shipping_details = {
                'name': request.form['full_name'], 'phone': request.form['phone'],
                'address1': request.form['address_line_1'], 'address2': request.form.get('address_line_2', ''),
                'city': request.form['city'], 'province': request.form['province'],
                'postal_code': request.form['postal_code']
            }

        payment_method = request.form['payment_method']

        # Validasi tambahan untuk tamu
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
            
            session['guest_order_details'] = { 'email': email_for_order, **shipping_details }

        # Membuat pesanan
        result = order_service.create_order(user_id_for_order, cart_data, shipping_details, payment_method)

        if result['success']:
            order_id = result['order_id']
            if not user_id_for_order:
                session['guest_order_id'] = order_id
            
            if payment_method == 'COD':
                flash(f"Pesanan #{order_id} berhasil dibuat! Siapkan pembayaran saat kurir tiba.", 'success')
                return redirect(url_for('user.order_success'))
            else:
                return redirect(url_for('user.payment_page', order_id=order_id))
        else:
            flash(result['message'], 'danger')
            return redirect(url_for('user.cart_page'))

    return render_template('user/checkout_page.html', user=user, content=get_content())

@user_bp.route('/checkout/edit_address', methods=['GET', 'POST'])
@login_required
def edit_address():
    """
    Menampilkan dan memproses form edit alamat dari halaman checkout.
    """
    user_id = session['user_id']
    if request.method == 'POST':
        address_data = {
            'phone': request.form['phone'], 'address1': request.form['address_line_1'],
            'address2': request.form.get('address_line_2', ''), 'city': request.form['city'],
            'province': request.form['province'], 'postal_code': request.form['postal_code']
        }
        result = user_service.update_user_address(user_id, address_data)
        flash(result['message'], 'success' if result['success'] else 'danger')
        return redirect(url_for('user.checkout'))

    user = user_service.get_user_by_id(user_id)
    return render_template('user/edit_address_page.html', user=user, content=get_content())