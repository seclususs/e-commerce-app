import json
from flask import render_template, request, session, redirect, url_for, flash
from db.db_config import get_db_connection, get_content
from services.users.auth_service import auth_service
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

    return render_template('auth/register.html', content=get_content(), hide_navbar=True)


@auth_bp.route('/register_from_order', methods=['POST'])
def register_from_order():
    order_details_str = request.form.get('order_details')
    password = request.form.get('password')
    order_id = request.form.get('order_id')