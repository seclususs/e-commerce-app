from flask import render_template, request, session, redirect, url_for, flash
from app.core.db import get_content, get_db_connection
from app.services.users.auth_service import auth_service
from . import auth_bp


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('product.products_page'))

    next_url = request.args.get('next')
    guest_session_id = session.get('session_id')

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = auth_service.verify_user_login(username, password)

        if user:
            user_id = user['id']
            session.clear()
            session['user_id'] = user_id
            session['username'] = user['username']
            session['is_admin'] = bool(user['is_admin'])
            session['just_logged_in'] = True

            if guest_session_id:
                conn = get_db_connection()
                try:
                    with conn:
                        conn.execute(
                            "UPDATE stock_holds SET user_id = ?, session_id = NULL WHERE session_id = ? AND user_id IS NULL",
                            (user_id, guest_session_id)
                        )
                    flash('Keranjang tamu Anda telah digabungkan.', 'info')
                except Exception as e:
                    print(f"Error transferring stock holds on login: {e}")
                    flash('Gagal menggabungkan keranjang tamu.', 'warning')
                finally:
                    conn.close()

            if session['is_admin']:
                flash('Login admin berhasil!', 'success')
                return redirect(url_for('admin.admin_dashboard'))
            else:
                flash('Anda berhasil login!', 'success')
                return redirect(next_url or url_for('product.products_page'))
        else:
            flash('Username atau password salah.', 'danger')

    return render_template('auth/login.html', content=get_content(), hide_navbar=True)