from flask import session, redirect, url_for, flash
from . import auth_bp


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Anda telah logout.', 'success')
    return redirect(url_for('product.index'))