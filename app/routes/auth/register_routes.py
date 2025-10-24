import json
from flask import render_template, request, session, redirect, url_for, flash
from app.core.db import get_db_connection, get_content
from app.services.users.auth_service import auth_service
from app.utils.logging_utils import get_logger
from . import auth_bp

logger = get_logger(__name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        logger.info(
            f"Pengguna {session['username']} sudah login, mengarahkan ulang dari halaman registrasi."
        )
        return redirect(url_for('product.products_page'))

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        logger.info(
            f"Percobaan registrasi untuk username: {username}, email: {email}"
        )

        try:
            new_user = auth_service.register_new_user(username, email, password)

            if new_user:
                session.clear()
                session['user_id'] = new_user['id']
                session['username'] = new_user['username']
                session['is_admin'] = bool(new_user['is_admin'])
                logger.info(
                    f"Registrasi berhasil untuk pengguna: {username} "
                    f"(ID: {new_user['id']}). Melakukan login otomatis."
                )
                flash('Registrasi berhasil! Selamat datang.', 'success')
                return redirect(url_for('product.products_page'))

            logger.warning(
                f"Registrasi gagal untuk username: {username}. "
                f"Username atau email kemungkinan sudah terdaftar."
            )
            flash('Username atau email sudah terdaftar.', 'danger')
            return redirect(url_for('auth.register'))

        except Exception as e:
            logger.error(
                f"Kesalahan saat registrasi untuk username {username}: {e}",
                exc_info=True
            )
            flash('Terjadi kesalahan saat pendaftaran.', 'danger')
            return redirect(url_for('auth.register'))

    logger.debug("Menampilkan halaman registrasi.")
    return render_template(
        'auth/register.html',
        content=get_content(),
        hide_navbar=True
    )


@auth_bp.route('/register_from_order', methods=['POST'])
def register_from_order():
    order_details_str = request.form.get('order_details')
    password = request.form.get('password')
    order_id = request.form.get('order_id')

    logger.info(
        f"Mencoba mendaftarkan pengguna dari pesanan tamu dengan ID: {order_id}"
    )

    if not order_details_str or not password or not order_id:
        logger.warning(
            f"Registrasi dari pesanan gagal: Data tidak lengkap. "
            f"ID Pesanan: {order_id}"
        )
        flash('Data pendaftaran tidak lengkap.', 'danger')
        return redirect(url_for('purchase.order_success'))

    try:
        order_details = json.loads(order_details_str)
        email = order_details.get('email')

        if not email:
            raise ValueError("Email tidak ditemukan dalam detail pesanan")

        logger.debug(
            f"Detail pesanan berhasil dimuat untuk registrasi. Email: {email}"
        )

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(
            f"Kesalahan saat memproses detail pesanan atau email hilang untuk "
            f"registrasi dari pesanan {order_id}: {e}",
            exc_info=True
        )
        flash('Data pesanan tidak valid.', 'danger')
        return redirect(url_for('purchase.order_success'))

    conn = None
    cursor = None

    try:
        new_user = auth_service.register_guest_user(order_details, password)

        if new_user:
            logger.info(
                f"Pengguna tamu berhasil didaftarkan dari pesanan {order_id}. "
                f"ID Pengguna Baru: {new_user['id']}, Username: {new_user['username']}"
            )

            session.clear()
            session['user_id'] = new_user['id']
            session['username'] = new_user['username']
            session['is_admin'] = bool(new_user['is_admin'])

            conn = get_db_connection()
            cursor = conn.cursor()

            try:
                cursor.execute(
                    'UPDATE orders SET user_id = %s WHERE id = %s AND user_id IS NULL',
                    (new_user['id'], order_id)
                )
                conn.commit()

                if cursor.rowcount > 0:
                    logger.info(
                        f"Pesanan {order_id} berhasil dikaitkan dengan "
                        f"pengguna baru {new_user['id']}."
                    )
                else:
                    logger.warning(
                        f"Gagal mengaitkan pesanan {order_id} dengan "
                        f"pengguna baru {new_user['id']}. Pesanan mungkin "
                        f"sudah memiliki ID pengguna atau ID tidak valid."
                    )

            except Exception as db_e:
                conn.rollback()
                logger.error(
                    f"Kesalahan saat mengaitkan pesanan {order_id} dengan pengguna "
                    f"{new_user['id']}: {db_e}",
                    exc_info=True
                )
                flash(
                    'Gagal mengaitkan pesanan dengan akun baru Anda.',
                    'warning'
                )

            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()

            flash('Akun berhasil dibuat dan Anda telah login!', 'success')
            return redirect(url_for('user.user_profile'))

        logger.warning(
            f"Gagal mendaftarkan pengguna tamu dari pesanan {order_id}. "
            f"Email {email} mungkin sudah terdaftar."
        )
        flash('Gagal membuat akun. Email mungkin sudah terdaftar.', 'danger')
        session['guest_order_details'] = order_details
        session['guest_order_id'] = order_id
        return redirect(url_for('purchase.order_success'))

    except Exception as e:
        logger.error(
            f"Kesalahan tak terduga saat registrasi dari pesanan {order_id}: {e}",
            exc_info=True
        )
        flash('Terjadi kesalahan server saat membuat akun.', 'danger')
        session['guest_order_details'] = order_details
        session['guest_order_id'] = order_id
        return redirect(url_for('purchase.order_success'))

    finally:
        if conn and conn.is_connected():
            if cursor:
                cursor.close()
            conn.close()