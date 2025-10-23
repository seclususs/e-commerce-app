from flask import render_template, request, flash, redirect, url_for, jsonify
from app.core.db import get_content
from app.services.users.auth_service import auth_service
from . import auth_bp


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')

        auth_service.handle_password_reset_request(email)
        message = 'Jika email terdaftar, link reset password telah dikirim.'

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': message})

        flash(f'SIMULASI: {message}', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html', content=get_content(), hide_navbar=True)