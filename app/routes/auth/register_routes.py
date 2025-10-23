import json
from flask import render_template, request, session, redirect, url_for, flash
from app.core.db import get_db_connection, get_content
from app.services.users.auth_service import auth_service
from . import auth_bp


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('product.products_page'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        new_user = auth_service.register_new_user(username, email, password)

        if new_user:
            session.clear()
            session['user_id'] = new_user['id']
            session['username'] = new_user['username']
            session['is_admin'] = bool(new_user['is_admin'])

            flash('Registrasi berhasil! Selamat datang.', 'success')
            return redirect(url_for('product.products_page'))
        else:
            flash('Username atau email sudah terdaftar.', 'danger')
            return redirect(url_for('auth.register'))

    return render_template('auth/register.html', content=get_content(), hide_navbar=True)


@auth_bp.route('/register_from_order', methods=['POST'])
def register_from_order():
    order_details_str = request.form.get('order_details')
    password = request.form.get('password')
    order_id = request.form.get('order_id')

    if not order_details_str or not password or not order_id:
        flash('Data pendaftaran tidak lengkap.', 'danger')
        return redirect(url_for('purchase.order_success'))

    try:
        order_details = json.loads(order_details_str)
    except json.JSONDecodeError:
        flash('Data pesanan tidak valid.', 'danger')
        return redirect(url_for('purchase.order_success'))
    
    new_user = auth_service.register_guest_user(order_details, password)

    if new_user:
        session.clear()
        session['user_id'] = new_user['id']
        session['username'] = new_user['username']
        session['is_admin'] = bool(new_user['is_admin'])

        conn = get_db_connection()
        try:
            conn.execute('UPDATE orders SET user_id = ? WHERE id = ? AND user_id IS NULL', (new_user['id'], order_id))
            conn.commit()
        except Exception as e:
            print(f"Error associating order {order_id} with user {new_user['id']}: {e}")
            flash('Gagal mengaitkan pesanan dengan akun baru Anda.', 'warning')
        finally:
            conn.close()

        flash('Akun berhasil dibuat dan Anda telah login!', 'success')
        return redirect(url_for('user.user_profile'))
    else:
        flash('Gagal membuat akun. Email mungkin sudah terdaftar.', 'danger')
        session['guest_order_details'] = order_details
        session['guest_order_id'] = order_id
        return redirect(url_for('purchase.order_success'))