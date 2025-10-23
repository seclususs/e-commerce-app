from flask import jsonify, request, abort, current_app
from . import api_bp
from services.orders.payment_service import payment_service
from services.utils.scheduler_service import scheduler_service


@api_bp.route('/payment-webhook', methods=['POST'])
def payment_webhook():
    secret_key = current_app.config['SECRET_KEY']

    auth_header = request.headers.get('X-API-Key')
    if auth_header != secret_key:
        abort(401, description="Unauthorized")

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid JSON payload.'}), 400

    event_type = data.get('event')
    transaction_id = data.get('transaction_id')
    status = data.get('status')

    if event_type == 'payment_status_update' and status == 'success' and transaction_id:
        result = payment_service.process_successful_payment(transaction_id)
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500

    return jsonify({'success': True, 'message': 'Webhook received and acknowledged.'}), 200


@api_bp.route('/run-scheduler-jobs', methods=['POST'])
def run_scheduler_jobs():
    secret_key = current_app.config['SECRET_KEY']
    auth_header = request.headers.get('X-API-Key')
    if auth_header != secret_key:
        abort(401, description="Unauthorized")

    result = scheduler_service.cancel_expired_pending_orders()

    return jsonify(result), 200 if result['success'] else 500