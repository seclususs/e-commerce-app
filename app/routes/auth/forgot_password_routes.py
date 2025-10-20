from flask import render_template, request, flash, redirect, url_for
from database.db_config import get_content
from services.auth_service import auth_service
from . import auth_bp

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        
        auth_service.handle_password_reset_request(email)
        flash('SIMULASI: Jika email terdaftar, email reset password telah dikirim.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html', content=get_content(), hide_navbar=True)