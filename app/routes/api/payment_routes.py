from typing import Any, Dict, Tuple

from flask import Response, current_app, jsonify, request

from app.exceptions.api_exceptions import AuthError, ValidationError
from app.exceptions.database_exceptions import (
    DatabaseException,
    RecordNotFoundError,
)
from app.exceptions.service_exceptions import (
    InvalidOperationError,
    OutOfStockError,
    PaymentFailedError,
    ServiceLogicError,
)
from app.services.orders.payment_service import payment_service
from app.utils.logging_utils import get_logger

from . import api_bp

logger = get_logger(__name__)


@api_bp.route("/payment-webhook", methods=["POST"])
def payment_webhook() -> Tuple[Response, int]:
    secret_key: str = current_app.config["SECRET_KEY"]
    auth_header: str | None = request.headers.get("X-API-Key")
    logger.info(
        f"Menerima webhook pembayaran. Header otentikasi ada: "
        f"{'Ya' if auth_header else 'Tidak'}"
    )

    if auth_header != secret_key:
        logger.warning("Percobaan webhook pembayaran tidak sah.")
        raise AuthError("Tidak diizinkan")

    data: Dict[str, Any] | None = request.get_json()

    if data is None:
        logger.error("Payload JSON tidak valid diterima pada webhook pembayaran.")
        raise ValidationError("Payload JSON tidak valid.")

    event_type: str | None = data.get("event")
    transaction_id: str | None = data.get("transaction_id")
    status: str | None = data.get("status")
    logger.info(
        f"Memproses event webhook: {event_type}, "
        f"ID Transaksi: {transaction_id}, Status: {status}"
    )

    if (
        event_type == "payment_status_update"
        and status == "success"
        and transaction_id
    ):
        
        try:
            result: Dict[str, Any] = (
                payment_service.process_successful_payment(transaction_id)
            )

            if result["success"]:
                logger.info(
                    "Pembayaran berhasil diproses untuk ID Transaksi: "
                    f"{transaction_id}. Hasil: {result['message']}"
                )
                return jsonify(result), 200
            
            else:
                logger.warning(
                    "Gagal memproses pembayaran untuk ID Transaksi: "
                    f"{transaction_id}. Alasan: {result['message']}"
                )
                if "stok habis" in result.get("message", "").lower():
                    raise OutOfStockError(result["message"])
                else:
                    raise PaymentFailedError(result["message"])

        except (
            RecordNotFoundError,
            InvalidOperationError,
            OutOfStockError,
            PaymentFailedError,
            DatabaseException,
            ServiceLogicError,
        ) as e:
            logger.error(
                "Error caught processing webhook for transaction "
                f"{transaction_id}: {e}",
                exc_info=True,
            )
            raise e
        
        except Exception as e:
            logger.error(
                "Terjadi kesalahan tak terduga saat memproses pembayaran untuk "
                f"ID Transaksi {transaction_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                "Terjadi kesalahan internal saat memproses pembayaran."
            )

    logger.info(
        "Webhook diterima dan diakui, tetapi tidak ada tindakan yang diambil "
        f"untuk event '{event_type}' dan status '{status}'."
    )
    return (
        jsonify({"success": True, "message": "Webhook diterima dan diakui."}),
        200,
    )