from flask import render_template, request, session, redirect, url_for, flash, current_app, jsonify
from app.core.db import get_db_connection, get_content
from app.utils.route_decorators import login_required
from app.services.orders.order_service import order_service
from app.utils.logging_utils import get_logger
from . import purchase_bp

logger = get_logger(__name__)


@purchase_bp.route('/order/pay/<int:order_id>')
def payment_page(order_id):
    user_id = session.get('user_id')
    guest_order_id = session.get('guest_order_id')
    log_identifier = (
        f"ID Pengguna {user_id}"
        if user_id
        else f"ID Pesanan Tamu {guest_order_id}"
    )
    logger.debug(
        f"Mengakses halaman pembayaran untuk ID Pesanan: {order_id}. "
        f"Identitas: {log_identifier}"
    )

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        order = None

        if user_id:
            cursor.execute(
                'SELECT * FROM orders WHERE id = %s AND user_id = %s',
                (order_id, user_id)
            )
            order = cursor.fetchone()

        elif guest_order_id and guest_order_id == order_id:
            cursor.execute(
                'SELECT * FROM orders WHERE id = %s AND user_id IS NULL',
                (order_id,)
            )
            order = cursor.fetchone()

        if not order:
            logger.warning(
                f"Pesanan {order_id} tidak ditemukan atau akses ditolak untuk {log_identifier}."
            )
            flash(
                "Pesanan tidak ditemukan atau tidak memerlukan pembayaran online.",
                "danger"
            )
            return redirect(url_for('product.index'))

        if order['payment_method'] == 'COD':
            logger.warning(
                f"Upaya mengakses halaman pembayaran untuk pesanan COD {order_id} oleh {log_identifier}."
            )
            flash(
                "Pesanan COD tidak memerlukan halaman pembayaran ini.",
                "info"
            )
            return redirect(url_for('purchase.order_success'))

        if order['status'] != 'Menunggu Pembayaran':
            logger.info(
                f"Halaman pembayaran diakses untuk pesanan {order_id}, tetapi statusnya adalah '{order['status']}', mengarahkan ulang."
            )
            flash(
                f"Status pesanan ini adalah '{order['status']}'. Tidak perlu pembayaran.",
                "info"
            )
            if user_id:
                return redirect(url_for('user.user_profile'))
            return redirect(url_for('product.index'))

        cursor.execute(
            '''
            SELECT p.name, oi.quantity, oi.price
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = %s
            ''',
            (order_id,)
        )
        items = cursor.fetchall()
        logger.info(
            f"Halaman pembayaran dimuat untuk ID Pesanan: {order_id}. Jumlah item: {len(items)}"
        )

        api_key = current_app.config['SECRET_KEY']
        return render_template(
            'purchase/payment_page.html',
            order=order,
            items=items,
            content=get_content(),
            api_key=api_key
        )

    except Exception as e:
        logger.error(
            f"Terjadi kesalahan saat memuat halaman pembayaran untuk pesanan {order_id}: {e}",
            exc_info=True
        )
        flash("Gagal memuat halaman pembayaran.", "danger")
        return redirect(url_for('product.index'))

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@purchase_bp.route('/order_success')
def order_success():
    guest_order_details = session.pop('guest_order_details', None)
    guest_order_id = session.pop('guest_order_id', None)
    session_id = session.pop('session_id', None)

    log_identifier = (
        f"ID Pengguna {session.get('user_id')}"
        if session.get('user_id')
        else f"ID Pesanan Tamu {guest_order_id}"
    )

    logger.info(
        f"Halaman keberhasilan pesanan diakses. Identitas: {log_identifier}. "
        f"Data pesanan tamu dihapus dari sesi: {'Ya' if guest_order_details else 'Tidak'}"
    )

    return render_template(
        'purchase/success_page.html',
        content=get_content(),
        guest_order_details=guest_order_details,
        guest_order_id=guest_order_id
    )


@purchase_bp.route('/order/cancel/<int:order_id>', methods=['POST'])
@login_required
def cancel_order(order_id):
    user_id = session['user_id']
    logger.info(
        f"Pengguna {user_id} mencoba membatalkan pesanan dengan ID: {order_id}"
    )

    try:
        result = order_service.cancel_user_order(order_id, user_id)
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if is_ajax:
            if result['success']:
                logger.info(
                    f"Pesanan {order_id} berhasil dibatalkan melalui AJAX oleh pengguna {user_id}."
                )
            else:
                logger.warning(
                    f"Gagal membatalkan pesanan {order_id} melalui AJAX oleh pengguna {user_id}. Alasan: {result['message']}"
                )
            return jsonify(result)

        flash(result['message'], 'success' if result['success'] else 'danger')

        if result['success']:
            logger.info(
                f"Pesanan {order_id} berhasil dibatalkan oleh pengguna {user_id}."
            )
        else:
            logger.warning(
                f"Gagal membatalkan pesanan {order_id} oleh pengguna {user_id}. Alasan: {result['message']}"
            )
        return redirect(url_for('user.user_profile'))

    except Exception as e:
        logger.error(
            f"Terjadi kesalahan saat membatalkan pesanan {order_id} untuk pengguna {user_id}: {e}",
            exc_info=True
        )
        flash("Terjadi kesalahan saat membatalkan pesanan.", "danger")

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(
                {'success': False, 'message': 'Terjadi kesalahan server.'}
            ), 500

        return redirect(url_for('user.user_profile'))