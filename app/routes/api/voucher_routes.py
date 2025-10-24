from flask import jsonify, request
from app.services.orders.voucher_service import voucher_service
from app.utils.logging_utils import get_logger
from . import api_bp

logger = get_logger(__name__)


@api_bp.route('/apply-voucher', methods=['POST'])
def apply_voucher():
    data = request.get_json()
    code = data.get('voucher_code')
    subtotal = data.get('subtotal')

    logger.debug(
        f"Mencoba menerapkan kode voucher: {code} untuk subtotal: {subtotal}"
    )

    if not code or subtotal is None:
        logger.warning(
            f"Permintaan penerapan voucher tidak valid. "
            f"Kode: {code}, Subtotal: {subtotal}"
        )
        return jsonify(
            {
                'success': False,
                'message': 'Kode voucher dan subtotal diperlukan.'
            }
        ), 400

    try:
        subtotal_float = float(subtotal)
        result = voucher_service.validate_and_calculate_voucher(
            code, subtotal_float
        )

        if result['success']:
            logger.info(
                f"Voucher '{code}' berhasil diterapkan. "
                f"Diskon: {result['discount_amount']}"
            )
        else:
            logger.info(
                f"Penerapan voucher '{code}' gagal. "
                f"Alasan: {result['message']}"
            )

        return jsonify(result)

    except ValueError:
        logger.error(
            f"Format subtotal tidak valid: {subtotal}", exc_info=True
        )
        return jsonify(
            {
                'success': False,
                'message': 'Format subtotal tidak valid.'
            }
        ), 400

    except Exception as e:
        logger.error(
            f"Kesalahan saat menerapkan voucher '{code}': {e}", exc_info=True
        )
        return jsonify(
            {
                'success': False,
                'message': 'Gagal memvalidasi voucher.'
            }
        ), 500