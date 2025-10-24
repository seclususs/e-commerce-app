import mysql.connector
from flask import render_template, request, session, redirect, url_for, flash
from app.core.db import get_content, get_db_connection
from app.services.users.auth_service import auth_service
from app.utils.logging_utils import get_logger
from . import auth_bp

logger = get_logger(__name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        logger.info(
            f"Pengguna {session['username']} (ID: {session['user_id']}) sudah login, mengarahkan ulang."
        )
        return redirect(url_for('product.products_page'))

    next_url = request.args.get('next')
    guest_session_id = session.get('session_id')
    logger.debug(
        f"Halaman login diakses. URL berikutnya: {next_url}, "
        f"ID Sesi Tamu: {guest_session_id}"
    )

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        logger.info(f"Percobaan login untuk username: {username}")

        user = auth_service.verify_user_login(username, password)

        if user:
            user_id = user['id']
            logger.info(
                f"Login berhasil untuk pengguna: {username} (ID: {user_id}), "
                f"Admin: {bool(user['is_admin'])}"
            )

            session.clear()
            session['user_id'] = user_id
            session['username'] = user['username']
            session['is_admin'] = bool(user['is_admin'])
            session['just_logged_in'] = True

            if guest_session_id:
                conn = None

                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    logger.debug(
                        f"Mencoba memindahkan data penahanan stok dari "
                        f"sesi {guest_session_id} ke pengguna {user_id}"
                    )

                    cursor.execute(
                        """
                        UPDATE stock_holds
                        SET user_id = %s, session_id = NULL
                        WHERE session_id = %s AND user_id IS NULL
                        """,
                        (user_id, guest_session_id)
                    )
                    conn.commit()

                    if cursor.rowcount > 0:
                        logger.info(
                            f"Berhasil memindahkan {cursor.rowcount} "
                            f"data penahanan stok untuk pengguna {user_id}"
                        )
                        flash('Keranjang tamu Anda telah digabungkan.', 'info')
                    else:
                        logger.info(
                            f"Tidak ada data penahanan stok yang dipindahkan "
                            f"untuk sesi {guest_session_id}"
                        )

                except mysql.connector.Error as e:
                    if conn:
                        conn.rollback()
                    logger.error(
                        f"Terjadi kesalahan saat memindahkan data penahanan stok "
                        f"saat login untuk pengguna {user_id}: {e}",
                        exc_info=True
                    )
                    flash('Gagal menggabungkan keranjang tamu.', 'warning')

                finally:
                    if conn and conn.is_connected():
                        cursor.close()
                        conn.close()

            if session['is_admin']:
                flash('Login admin berhasil!', 'success')
                return redirect(url_for('admin.admin_dashboard'))

            flash('Anda berhasil login!', 'success')
            redirect_target = next_url or url_for('product.products_page')
            logger.info(f"Mengarahkan pengguna {username} ke {redirect_target}")
            return redirect(redirect_target)

        logger.warning(f"Login gagal untuk username: {username}")
        flash('Username atau password salah.', 'danger')

    return render_template(
        'auth/login.html',
        content=get_content(),
        hide_navbar=True
    )