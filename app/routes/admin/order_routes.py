import json
import mysql.connector
from decimal import Decimal
from flask import render_template, request, jsonify, redirect, flash, url_for
from app.core.db import get_db_connection, get_content
from app.utils.route_decorators import admin_required
from app.services.orders.order_service import order_service
from app.utils.logging_utils import get_logger
from . import admin_bp

logger = get_logger(__name__)


@admin_bp.route('/orders')
@admin_required
def admin_orders():
    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        status_filter = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        search_query = request.args.get('search')

        logger.debug(
            f"Mengambil data pesanan dengan filter - "
            f"Status: {status_filter}, Awal: {start_date}, Akhir: {end_date}, Pencarian: {search_query}"
        )

        query = (
            'SELECT o.*, u.username AS customer_name FROM orders o '
            'LEFT JOIN users u ON o.user_id = u.id WHERE 1=1'
        )
        params = []

        if status_filter:
            query += ' AND o.status = %s'
            params.append(status_filter)

        if start_date:
            query += ' AND DATE(o.order_date) >= %s'
            params.append(start_date)

        if end_date:
            query += ' AND DATE(o.order_date) <= %s'
            params.append(end_date)

        if search_query:
            query += (
                " AND (CAST(o.id AS CHAR) LIKE %s "
                "OR u.username LIKE %s "
                "OR o.shipping_name LIKE %s)"
            )
            search_term = f'%{search_query}%'
            params.extend([search_term, search_term, search_term])

        query += ' ORDER BY o.order_date DESC'

        cursor.execute(query, tuple(params))
        orders = cursor.fetchall()
        logger.info(f"Berhasil mengambil {len(orders)} data pesanan sesuai filter.")

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            logger.debug("Mengembalikan respon JSON untuk permintaan AJAX.")
            html = render_template(
                'admin/partials/_order_table_body.html',
                orders=orders
            )
            return jsonify({'success': True, 'html': html})

        logger.info("Menampilkan halaman kelola pesanan.")
        return render_template(
            'admin/manage_orders.html',
            orders=orders,
            content=get_content()
        )

    except mysql.connector.Error as db_err:
        logger.error(
            f"Kesalahan database saat mengambil data pesanan: {db_err}",
            exc_info=True
        )
        flash("Terjadi kesalahan database saat mengambil data pesanan.", "danger")
        return render_template(
            'admin/manage_orders.html', orders=[], content=get_content()
        )

    except Exception as e:
        logger.error(
            f"Kesalahan tak terduga saat mengambil data pesanan: {e}",
            exc_info=True
        )
        flash("Terjadi kesalahan saat mengambil data pesanan.", "danger")
        return render_template(
            'admin/manage_orders.html', orders=[], content=get_content()
        )

    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


@admin_bp.route('/order/<int:id>')
@admin_required
def admin_order_detail(id):
    conn = None
    logger.debug(f"Mengambil detail pesanan dengan ID: {id}")

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            'SELECT o.*, u.username AS customer_name, u.email '
            'FROM orders o LEFT JOIN users u ON o.user_id = u.id '
            'WHERE o.id = %s',
            (id,)
        )
        order = cursor.fetchone()

        if not order:
            logger.warning(f"Pesanan dengan ID {id} tidak ditemukan.")
            flash('Pesanan tidak ditemukan.', 'danger')
            return redirect(url_for('admin.admin_orders'))

        cursor.execute(
            'SELECT p.name, oi.quantity, oi.price, oi.size_at_order '
            'FROM order_items oi JOIN products p ON oi.product_id = p.id '
            'WHERE oi.order_id = %s',
            (id,)
        )
        items = cursor.fetchall()

        logger.info(
            f"Detail pesanan berhasil diambil untuk ID {id}. "
            f"Jumlah item: {len(items)}"
        )

        return render_template(
            'admin/view_order.html',
            order=order,
            items=items,
            content=get_content()
        )

    except mysql.connector.Error as db_err:
        logger.error(
            f"Kesalahan database saat mengambil detail pesanan ID {id}: {db_err}",
            exc_info=True
        )
        flash("Terjadi kesalahan database saat mengambil detail pesanan.", "danger")
        return redirect(url_for('admin.admin_orders'))

    except Exception as e:
        logger.error(
            f"Kesalahan tak terduga saat mengambil detail pesanan ID {id}: {e}",
            exc_info=True
        )
        flash("Terjadi kesalahan saat mengambil detail pesanan.", "danger")
        return redirect(url_for('admin.admin_orders'))

    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


@admin_bp.route('/order/invoice/<int:id>')
@admin_required
def admin_order_invoice(id):
    conn = None
    logger.debug(f"Menghasilkan invoice untuk pesanan ID: {id}")

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            'SELECT o.*, u.email FROM orders o '
            'LEFT JOIN users u ON o.user_id = u.id WHERE o.id = %s',
            (id,)
        )
        order = cursor.fetchone()

        if not order:
            logger.warning(
                f"Pesanan dengan ID {id} tidak ditemukan saat membuat invoice."
            )
            return "Pesanan tidak ditemukan", 404

        cursor.execute(
            'SELECT p.name, oi.quantity, oi.price '
            'FROM order_items oi JOIN products p ON oi.product_id = p.id '
            'WHERE oi.order_id = %s',
            (id,)
        )
        items = cursor.fetchall()

        logger.info(f"Data invoice berhasil diambil untuk pesanan ID: {id}")

        return render_template(
            'admin/invoice.html',
            order=order,
            items=items,
            content=get_content()
        )

    except mysql.connector.Error as db_err:
        logger.error(
            f"Kesalahan database saat membuat invoice untuk pesanan ID {id}: {db_err}",
            exc_info=True
        )
        return "Gagal membuat invoice karena kesalahan database", 500

    except Exception as e:
        logger.error(
            f"Kesalahan saat membuat invoice untuk pesanan ID {id}: {e}",
            exc_info=True
        )
        return "Gagal membuat invoice", 500

    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


@admin_bp.route('/update_order_status/<int:id>', methods=['POST'])
@admin_required
def update_order_status(id):
    status = request.form.get('status')
    tracking_number = request.form.get('tracking_number')

    logger.debug(
        f"Memperbarui pesanan ID: {id}. "
        f"Status baru: {status}, Nomor resi: {tracking_number}"
    )

    try:
        result = order_service.update_order_status_and_tracking(
            id, status, tracking_number
        )

        if result.get('success'):
            logger.info(
                f"Pesanan ID {id} berhasil diperbarui. "
                f"Status: {status}, Resi: {tracking_number}. "
                f"Pesan: {result.get('message')}"
            )
            return jsonify(result)

        logger.warning(
            f"Gagal memperbarui pesanan ID {id}. "
            f"Alasan: {result.get('message')}"
        )
        return jsonify(result), 500

    except Exception as e:
        logger.error(
            f"Kesalahan saat memperbarui status pesanan ID {id}: {e}",
            exc_info=True
        )
        return jsonify({
            'success': False,
            'message': 'Gagal memperbarui status pesanan.'
        }), 500