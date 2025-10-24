from flask import jsonify, request, abort, current_app
from app.services.orders.payment_service import payment_service
from app.services.utils.scheduler_service import scheduler_service
from app.utils.logging_utils import get_logger
from . import api_bp

logger = get_logger(__name__)


@api_bp.route('/payment-webhook', methods=['POST'])
def payment_webhook():
    secret_key = current_app.config['SECRET_KEY']
    auth_header = request.headers.get('X-API-Key')
    logger.info(
        f"Menerima webhook pembayaran. Header otentikasi ada: "
        f"{'Ya' if auth_header else 'Tidak'}"
    )

    if auth_header != secret_key:
        logger.warning("Percobaan webhook pembayaran tidak sah.")
        abort(401, description="Tidak diizinkan")

    data = request.get_json()
    if data is None:
        logger.error("Payload JSON tidak valid diterima pada webhook pembayaran.")
        return jsonify({
            'success': False, 
            'message': 'Payload JSON tidak valid.'
            }), 400

    event_type = data.get('event')
    transaction_id = data.get('transaction_id')
    status = data.get('status')

    logger.info(
        f"Memproses event webhook: {event_type}, "
        f"ID Transaksi: {transaction_id}, Status: {status}"
    )

    if (
        event_type == 'payment_status_update'
        and status == 'success'
        and transaction_id
    ):
        try:
            result = payment_service.process_successful_payment(transaction_id)
            if result['success']:
                logger.info(
                    f"Pembayaran berhasil diproses untuk ID Transaksi: "
                    f"{transaction_id}. Hasil: {result['message']}"
                )
                return jsonify(result), 200

            logger.warning(
                f"Gagal memproses pembayaran untuk ID Transaksi: "
                f"{transaction_id}. Alasan: {result['message']}"
            )
            return jsonify(result), 500

        except Exception as e:
            logger.error(
                f"Terjadi kesalahan tak terduga saat memproses pembayaran untuk "
                f"ID Transaksi {transaction_id}: {e}",
                exc_info=True
            )
            return jsonify({
                'success': False,
                'message': 'Terjadi kesalahan internal saat memproses pembayaran.'
            }), 500

    logger.info(
        f"Webhook diterima dan diakui, tetapi tidak ada tindakan yang diambil untuk "
        f"event '{event_type}' dan status '{status}'."
    )
    return jsonify({
        'success': True,
        'message': 'Webhook diterima dan diakui.'
    }), 200


@api_bp.route('/run-scheduler-jobs', methods=['POST'])
def run_scheduler_jobs():
    secret_key = current_app.config['SECRET_KEY']
    auth_header = request.headers.get('X-API-Key')
    logger.info(
        f"Menerima permintaan untuk menjalankan tugas scheduler. Header otentikasi ada: "
        f"{'Ya' if auth_header else 'Tidak'}"
    )

    if auth_header != secret_key:
        logger.warning("Percobaan tidak sah untuk menjalankan tugas scheduler.")
        abort(401, description="Tidak diizinkan")

    try:
        logger.info("Menjalankan layanan scheduler: cancel_expired_pending_orders")
        result = scheduler_service.cancel_expired_pending_orders()
        logger.info(f"Tugas scheduler selesai dijalankan. Hasil: {result}")
        return jsonify(result), 200 if result['success'] else 500

    except Exception as e:
        logger.error(
            f"Terjadi kesalahan saat menjalankan tugas scheduler melalui API: {e}",
            exc_info=True
        )
        return jsonify({
            'success': False,
            'message': 'Terjadi kesalahan internal saat menjalankan tugas scheduler.'
        }), 500