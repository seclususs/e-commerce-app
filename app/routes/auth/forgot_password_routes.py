from flask import render_template, request, flash, redirect, url_for, jsonify
from app.core.db import get_content
from app.services.users.auth_service import auth_service
from app.utils.logging_utils import get_logger
from . import auth_bp

logger = get_logger(__name__)


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        logger.info(f"Permintaan reset password untuk email: {email}")

        try:
            auth_service.handle_password_reset_request(email)
            message = (
                'Jika email terdaftar, link reset password telah dikirim.'
            )
            logger.info(
                f"Simulasi reset password dimulai untuk email: {email}"
            )

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                logger.debug(
                    "Merespons dengan JSON untuk permintaan reset password melalui AJAX."
                )
                return jsonify({'success': True, 'message': message})

            flash(f"SIMULASI: {message}", 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            logger.error(
                f"Kesalahan saat menangani permintaan reset password untuk email {email}: {e}",
                exc_info=True
            )
            flash(
                "Terjadi kesalahan saat memproses permintaan reset password.",
                'danger'
            )

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(
                    {'success': False, 'message': 'Terjadi kesalahan server.'}
                ), 500

            return redirect(url_for('auth.forgot_password'))

    logger.debug("Menampilkan halaman lupa password.")
    return render_template(
        'auth/forgot_password.html',
        content=get_content(),
        hide_navbar=True
    )