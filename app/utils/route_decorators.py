from functools import wraps
from flask import session, flash, redirect, url_for


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Anda harus login untuk mengakses halaman ini.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash("Hanya admin yang dapat mengakses halaman ini.", "danger")
            return redirect(url_for('product.products_page'))
        return f(*args, **kwargs)
    return decorated_function