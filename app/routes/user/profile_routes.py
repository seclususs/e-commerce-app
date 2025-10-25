import mysql.connector
from flask import render_template, request, session, redirect, url_for, flash, jsonify, abort
from app.core.db import get_db_connection, get_content
from app.utils.route_decorators import login_required
from app.services.users.user_service import user_service
from app.utils.logging_utils import get_logger
from . import user_bp

logger = get_logger(__name__)


@user_bp.route('/profile')
@login_required
def user_profile():
    user_id = session['user_id']
    logger.debug(f"Mengakses halaman profil untuk ID pengguna: {user_id}")

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()

        if not user:
            logger.error(
                f"Kesalahan akses profil: ID pengguna {user_id} tidak ditemukan di database."
            )
            session.clear()
            flash("Sesi Anda tidak valid, silakan login kembali.", "danger")
            return redirect(url_for('auth.login'))

        cursor.execute(
            'SELECT * FROM orders WHERE user_id = %s ORDER BY order_date DESC',
            (user_id,)
        )
        orders = cursor.fetchall()
        logger.info(
            f"Berhasil mengambil profil dan {len(orders)} pesanan untuk ID pengguna: {user_id}"
        )

        return render_template(
            'user/user_profile.html',
            user=user,
            orders=orders,
            content=get_content()
        )

    except mysql.connector.Error as db_err:
        logger.error(
            f"Kesalahan database saat mengambil profil untuk ID pengguna {user_id}: {db_err}",
            exc_info=True
        )
        flash("Gagal memuat profil Anda karena kesalahan database.", "danger")
        return render_template(
            'user/user_profile.html',
            user={'username': session.get('username', 'Pengguna'), 'email': 'N/A'},
            orders=[],
            content=get_content()
        )

    except Exception as e:
        logger.error(
            f"Kesalahan tak terduga saat mengambil profil untuk ID pengguna {user_id}: {e}",
            exc_info=True
        )
        flash("Gagal memuat profil Anda.", "danger")
        return render_template(
            'user/user_profile.html',
            user={'username': session.get('username', 'Pengguna'), 'email': 'N/A'},
            orders=[],
            content=get_content()
        )

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@user_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user_id = session['user_id']

    if request.method == 'POST':
        action = request.form.get('form_action')
        logger.debug(
            f"Memproses permintaan POST edit profil untuk ID pengguna: {user_id}. "
            f"Aksi: {action}"
        )
        result = {}
        status_code = 200

        try:
            if action == 'update_info':
                username = request.form['username']
                email = request.form['email']
                logger.info(
                    f"Memanggil service update_user_info untuk pengguna {user_id}. Nama baru: {username}, Email baru: {email}"
                )
                result = user_service.update_user_info(user_id, username, email)
                if result.get('success'):
                    session['username'] = username
                    result['data'] = {'username': username, 'email': email}
                else:
                    status_code = 400

            elif action == 'change_password':
                current_password = request.form['current_password']
                new_password = request.form['new_password']
                logger.info(f"Memanggil service change_user_password untuk pengguna {user_id}.")
                result = user_service.change_user_password(
                    user_id, current_password, new_password
                )
                if not result.get('success'):
                    status_code = 400

            elif action == 'update_address':
                address_data = {
                    'phone': request.form['phone'],
                    'address1': request.form['address_line_1'],
                    'address2': request.form.get('address_line_2', ''),
                    'city': request.form['city'],
                    'province': request.form['province'],
                    'postal_code': request.form['postal_code']
                }
                logger.info(
                    f"Memanggil service update_user_address untuk pengguna {user_id}."
                )
                result = user_service.update_user_address(user_id, address_data)
                if result.get('success'):
                    result['data'] = request.form.to_dict() # Mengirim kembali data form untuk update UI jika perlu
                else:
                    status_code = 400
            else:
                logger.warning(
                    f"Aksi tidak valid '{action}' diterima untuk pengguna {user_id}."
                )
                result = {'success': False, 'message': 'Aksi tidak dikenal.'}
                status_code = 400

        except Exception as e:
            logger.error(
                f"Kesalahan saat memproses aksi edit profil '{action}' untuk pengguna {user_id}: {e}",
                exc_info=True
            )
            result = {'success': False, 'message': 'Terjadi kesalahan server.'}
            status_code = 500

        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if is_ajax:
            logger.debug(
                f"Mengirim respons JSON. Aksi: '{action}', Berhasil: {result.get('success')}"
            )
            return jsonify(result), status_code

        flash(
            result.get('message', 'Terjadi kesalahan.'),
            'success' if result.get('success') else 'danger'
        )
        return redirect(url_for('user.edit_profile'))

    logger.debug(
        f"Mengakses halaman edit profil (GET) untuk ID pengguna: {user_id}"
    )
    try:
        user = user_service.get_user_by_id(user_id)
        if not user:
            logger.error(
                f"Kesalahan akses halaman edit profil: ID pengguna {user_id} tidak ditemukan."
            )
            session.clear()
            flash("Sesi Anda tidak valid, silakan login kembali.", "danger")
            return redirect(url_for('auth.login'))

        return render_template(
            'user/profile_editor.html',
            user=user,
            content=get_content()
        )
    except Exception as e:
        logger.error(
            f"Kesalahan saat memuat halaman edit profil untuk pengguna {user_id}: {e}",
            exc_info=True
        )
        flash("Gagal memuat halaman edit profil.", "danger")
        return redirect(url_for('user.user_profile'))


@user_bp.route('/order/track/<int:order_id>')
@login_required
def track_order(order_id):
    user_id = session['user_id']
    logger.debug(
        f"Pengguna {user_id} meminta pelacakan untuk ID pesanan: {order_id}"
    )

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            'SELECT * FROM orders WHERE id = %s AND user_id = %s',
            (order_id, user_id)
        )
        order = cursor.fetchone()

        if not order:
            logger.warning(
                f"Pesanan {order_id} tidak ditemukan atau akses ditolak untuk pengguna {user_id}."
            )
            abort(
                404,
                description="Pesanan tidak ditemukan atau Anda tidak memiliki akses."
            )

        cursor.execute(
            """
            SELECT oi.*, p.name
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = %s
            """,
            (order_id,)
        )
        items = cursor.fetchall()

        cursor.execute(
            """
            SELECT *
            FROM order_status_history
            WHERE order_id = %s
            ORDER BY timestamp DESC
            """,
            (order_id,)
        )
        history_list = cursor.fetchall()

        logger.info(
            f"Data pelacakan berhasil diambil. {len(items)} item, {len(history_list)} riwayat status ditemukan."
        )

        return render_template(
            'user/order_tracking.html',
            order=order,
            items=items,
            history_list=history_list,
            content=get_content()
        )

    except mysql.connector.Error as db_err:
        logger.error(
            f"Kesalahan database saat mengambil data pelacakan untuk pesanan {order_id}: {db_err}",
            exc_info=True
        )
        flash(
            "Gagal memuat informasi pelacakan karena kesalahan database.",
            "danger"
        )
        return redirect(url_for('user.user_profile'))

    except Exception as e:
        logger.error(
            f"Kesalahan tak terduga saat mengambil data pelacakan untuk pesanan {order_id}: {e}",
            exc_info=True
        )
        flash("Gagal memuat informasi pelacakan.", "danger")
        return redirect(url_for('user.user_profile'))

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()