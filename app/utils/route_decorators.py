from functools import wraps
from flask import session, flash, redirect, url_for
from app.utils.logging_utils import get_logger


logger = get_logger(__name__)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            logger.debug(
                f"Akses ditolak untuk rute {f.__name__}: Pengguna belum login."
            )
            flash("Anda harus login untuk mengakses halaman ini.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            user_id = session.get('user_id', 'Unknown')
            logger.warning(
                f"Akses admin ditolak untuk rute {f.__name__}. "
                f"ID Pengguna: {user_id} bukan admin."
            )
            flash("Hanya admin yang dapat mengakses halaman ini.", "danger")
            return redirect(url_for('product.products_page'))
        return f(*args, **kwargs)

    return decorated_function