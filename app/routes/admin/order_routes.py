import json
import mysql.connector
from decimal import Decimal
from flask import render_template, request, jsonify, redirect, flash, url_for
from app.core.db import get_db_connection, get_content
from app.utils.route_decorators import admin_required
from app.services.orders.order_service import order_service
from app.services.orders.order_query_service import order_query_service
from app.utils.logging_utils import get_logger
from . import admin_bp

logger = get_logger(__name__)


@admin_bp.route('/orders')
@admin_required
def admin_orders():
    try:
        status_filter = request.args.get('status')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        search_query = request.args.get('search')

        logger.debug(
            f"Mengambil data pesanan dengan filter - "
            f"Status: {status_filter}, Awal: {start_date}, Akhir: {end_date}, Pencarian: {search_query}"
        )

        orders = order_query_service.get_filtered_admin_orders(
            status=status_filter,
            start_date=start_date,
            end_date=end_date,
            search=search_query
        )
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

    except Exception as e:
        logger.error(
            f"Kesalahan saat mengambil data pesanan: {e}",
            exc_info=True
        )
        flash("Terjadi kesalahan saat mengambil data pesanan.", "danger")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': 'Gagal mengambil data pesanan.'
            }), 500
        return render_template(
            'admin/manage_orders.html', orders=[], content=get_content()
        )


@admin_bp.route('/order/<int:id>')
@admin_required
def admin_order_detail(id):
    logger.debug(f"Mengambil detail pesanan dengan ID: {id}")
    try:
        order, items = order_query_service.get_order_details_for_admin(id)

        if not order:
            logger.warning(f"Pesanan dengan ID {id} tidak ditemukan.")
            flash('Pesanan tidak ditemukan.', 'danger')
            return redirect(url_for('admin.admin_orders'))

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
    except Exception as e:
        logger.error(
            f"Kesalahan saat mengambil detail pesanan ID {id}: {e}",
            exc_info=True
        )
        flash("Terjadi kesalahan saat mengambil detail pesanan.", "danger")
        return redirect(url_for('admin.admin_orders'))


@admin_bp.route('/order/invoice/<int:id>')
@admin_required
def admin_order_invoice(id):
    logger.debug(f"Menghasilkan invoice untuk pesanan ID: {id}")
    try:
        order, items = order_query_service.get_order_details_for_invoice(id)

        if not order:
            logger.warning(
                f"Pesanan dengan ID {id} tidak ditemukan saat membuat invoice."
            )
            return "Pesanan tidak ditemukan", 404

        logger.info(f"Data invoice berhasil diambil untuk pesanan ID: {id}")
        return render_template(
            'admin/invoice.html',
            order=order,
            items=items,
            content=get_content()
        )
    except Exception as e:
        logger.error(
            f"Kesalahan saat membuat invoice untuk pesanan ID {id}: {e}",
            exc_info=True
        )
        return "Gagal membuat invoice", 500


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
        else:
            logger.warning(
                f"Gagal memperbarui pesanan ID {id}. "
                f"Alasan: {result.get('message')}"
            )
            status_code = result.get('status_code', 500)
            return jsonify(result), status_code

    except Exception as e:
        logger.error(
            f"Kesalahan saat memperbarui status pesanan ID {id}: {e}",
            exc_info=True
        )
        return jsonify({
            'success': False,
            'message': 'Gagal memperbarui status pesanan karena kesalahan server.'
        }), 500