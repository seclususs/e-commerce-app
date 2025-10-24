from flask import session, redirect, url_for, flash
from app.utils.logging_utils import get_logger
from . import auth_bp

logger = get_logger(__name__)


@auth_bp.route('/logout')
def logout():
    user_id = session.get('user_id')
    username = session.get('username')

    logger.info(
        f"Proses logout dimulai. Pengguna: {username} (ID: {user_id})"
    )

    session.clear()
    flash('Anda telah logout.', 'success')

    logger.info(
        f"Pengguna {username} (ID: {user_id}) berhasil logout."
    )

    return redirect(url_for('product.index'))