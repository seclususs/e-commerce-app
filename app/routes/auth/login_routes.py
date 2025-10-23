from flask import render_template, request, session, redirect, url_for, flash
from app.core.db import get_content
from app.services.users.auth_service import auth_service
from . import auth_bp


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
            session['just_logged_in'] = True

            if session['is_admin']:
                flash('Login admin berhasil!', 'success')
                return redirect(url_for('admin.admin_dashboard'))
            else:
                flash('Anda berhasil login!', 'success')
                return redirect(next_url or url_for('product.products_page'))
        else:
            flash('Username atau password salah.', 'danger')

    return render_template('auth/login.html', content=get_content(), hide_navbar=True)