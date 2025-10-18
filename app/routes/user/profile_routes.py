from flask import render_template, request, session, redirect, url_for, flash
from database.db_config import get_db_connection, get_content
from utils.route_decorators import login_required
from services.user_service import user_service

from . import user_bp

@user_bp.route('/profile')
@login_required
def user_profile():
    """
    Menampilkan halaman profil pengguna beserta riwayat pesanan.
    """
    user_id = session['user_id']
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    orders = conn.execute('SELECT * FROM orders WHERE user_id = ? ORDER BY order_date DESC', (user_id,)).fetchall()
    conn.close()
    return render_template('user/user_profile.html', user=user, orders=orders, content=get_content())

@user_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """
    Menampilkan dan memproses form untuk mengedit profil, alamat, dan password pengguna.
    """
    user_id = session['user_id']
    if request.method == 'POST':
        # Memperbarui info akun
        if 'update_info' in request.form:
            result = user_service.update_user_info(
                user_id, request.form['username'], request.form['email']
            )
            if result['success']:
                session['username'] = request.form['username']
            flash(result['message'], 'success' if result['success'] else 'danger')
        
        # Mengubah password
        elif 'change_password' in request.form:
            result = user_service.change_user_password(
                user_id, request.form['current_password'], request.form['new_password']
            )
            flash(result['message'], 'success' if result['success'] else 'danger')

        # Memperbarui alamat
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