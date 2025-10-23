from flask import jsonify, request
from . import api_bp
from app.services.orders.voucher_service import voucher_service


@api_bp.route('/apply-voucher', methods=['POST'])
def apply_voucher():
    data = request.get_json()
    code = data.get('voucher_code')
    subtotal = data.get('subtotal')

    if not code or subtotal is None:
        return jsonify({'success': False, 'message': 'Kode voucher dan subtotal diperlukan.'}), 400

    result = voucher_service.validate_and_calculate_voucher(code, float(subtotal))

    return jsonify(result)