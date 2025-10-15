import json
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from database.db_config import get_db_connection, get_content
from services.auth_service import auth_service

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('product.products_page'))
    
    next_url = request.args.get('next')
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = auth_service.verify_user_login(username, password)
        
        if user:
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = bool(user['is_admin'])
            
            if session['is_admin']:
                flash('Login admin berhasil!', 'success')
                return redirect(url_for('admin.admin_dashboard'))
            else:
                flash('Anda berhasil login!', 'success')
                return redirect(next_url or url_for('product.products_page'))
        else:
            flash('Username atau password salah.', 'danger')

    return render_template('auth/login.html', content=get_content(), hide_navbar=True)

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

    return render_template('auth/register.html', content=get_content(), hide_navbar=True)

@auth_bp.route('/register_from_order', methods=['POST'])
def register_from_order():
    order_details_str = request.form.get('order_details')
    password = request.form.get('password')
    order_id = request.form.get('order_id')
    
    if not order_details_str or not password or not order_id:
        flash("Informasi registrasi tidak lengkap.", "danger")
        return redirect(url_for('product.index'))
        
    order_details = json.loads(order_details_str)
    
    new_user = auth_service.register_guest_user(order_details, password)

    if new_user:
        conn = get_db_connection()
        conn.execute('UPDATE orders SET user_id = ? WHERE id = ?', (new_user['id'], order_id))
        conn.commit()
        conn.close()

        session.clear()
        session['user_id'] = new_user['id']
        session['username'] = new_user['username']
        session['is_admin'] = bool(new_user['is_admin'])
        flash('Akun berhasil dibuat! Pesanan Anda telah ditautkan.', 'success')
        return redirect(url_for('user.user_profile'))
    else:
        flash('Gagal membuat akun. Email mungkin sudah ada.', 'danger')
        return redirect(url_for('auth.login'))

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Anda telah logout.', 'success')
    return redirect(url_for('product.index'))