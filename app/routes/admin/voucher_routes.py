from flask import render_template, request, redirect, url_for, flash, jsonify
from app.core.db import get_content
from app.utils.route_decorators import admin_required
from app.services.orders.voucher_service import voucher_service
from app.utils.logging_utils import get_logger
from . import admin_bp

logger = get_logger(__name__)


@admin_bp.route('/vouchers', methods=['GET', 'POST'])
@admin_required
def admin_vouchers():
    if request.method == 'POST':
        code = request.form.get('code')
        v_type = request.form.get('type')
        value = request.form.get('value')
        min_purchase = request.form.get('min_purchase_amount')
        max_uses = request.form.get('max_uses')

        logger.debug(
            f"Route: Menerima permintaan POST untuk menambah voucher. Kode: {code}"
        )

        try:
            result = voucher_service.add_voucher(code, v_type, value, min_purchase, max_uses)

            if result.get('success'):
                logger.info(f"Route: Voucher '{code}' berhasil ditambahkan via service.")
                html = render_template(
                    'admin/partials/_voucher_row.html',
                    voucher=result['data']
                )
                result['html'] = html
                return jsonify(result)
            else:
                logger.warning(
                    f"Route: Gagal menambahkan voucher '{code}' via service. Alasan: {result.get('message')}"
                )
                return jsonify(result), 400

        except Exception as e:
            logger.error(
                f"Route: Terjadi kesalahan saat memanggil service add_voucher untuk kode '{code}': {e}",
                exc_info=True
            )
            return jsonify({
                'success': False,
                'message': 'Gagal menambahkan voucher karena kesalahan server.'
            }), 500

    logger.debug("Route: Permintaan GET ke /vouchers. Mengambil data voucher via service...")
    try:
        vouchers = voucher_service.get_all_vouchers()
        logger.info(f"Route: Berhasil mengambil {len(vouchers)} data voucher dari service.")
        return render_template(
            'admin/manage_vouchers.html',
            vouchers=vouchers,
            content=get_content()
        )
    except Exception as e:
        logger.error(f"Route: Kesalahan saat mengambil voucher dari service: {e}", exc_info=True)
        flash("Gagal memuat halaman voucher.", "danger")
        return render_template(
            'admin/manage_vouchers.html',
            vouchers=[],
            content=get_content()
        )


@admin_bp.route('/vouchers/delete/<int:id>', methods=['POST'])
@admin_required
def delete_voucher(id):
    logger.debug(f"Route: Menerima permintaan POST untuk menghapus voucher ID: {id}")
    try:
        result = voucher_service.delete_voucher_by_id(id)
        if result.get('success'):
            logger.info(f"Route: Voucher ID {id} berhasil dihapus via service.")
        else:
            logger.warning(
                f"Route: Gagal menghapus voucher ID {id} via service. Alasan: {result.get('message')}"
            )
        status_code = 200 if result.get('success') else (404 if result.get('message') == 'Voucher tidak ditemukan.' else 500)
        return jsonify(result), status_code
    except Exception as e:
        logger.error(
            f"Route: Terjadi kesalahan saat memanggil service delete_voucher_by_id untuk ID {id}: {e}",
            exc_info=True
        )
        return jsonify({
            'success': False,
            'message': 'Gagal menghapus voucher karena kesalahan server.'
        }), 500


@admin_bp.route('/vouchers/toggle/<int:id>', methods=['POST'])
@admin_required
def toggle_voucher(id):
    logger.debug(f"Route: Menerima permintaan POST untuk mengubah status voucher ID: {id}")
    try:
        result = voucher_service.toggle_voucher_status(id)
        if result.get('success'):
            logger.info(f"Route: Status voucher ID {id} berhasil diubah via service.")
        else:
            logger.warning(
                f"Route: Gagal mengubah status voucher ID {id} via service. Alasan: {result.get('message')}"
            )
        status_code = 200 if result.get('success') else (404 if result.get('message') == 'Voucher tidak ditemukan.' else 500)
        return jsonify(result), status_code
    except Exception as e:
        logger.error(
            f"Route: Terjadi kesalahan saat memanggil service toggle_voucher_status untuk ID {id}: {e}",
            exc_info=True
        )
        return jsonify({
            'success': False,
            'message': 'Gagal mengubah status voucher karena kesalahan server.'
        }), 500