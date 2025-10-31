from typing import Any, Dict, Tuple

from flask import Response, jsonify, request

from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.services.orders.discount_service import discount_service
from app.utils.logging_utils import get_logger

from . import api_bp

logger = get_logger(__name__)


@api_bp.route("/apply-voucher", methods=["POST"])
def apply_voucher() -> Tuple[Response, int]:
    data: Dict[str, Any] | None = request.get_json()
    if not data:
        return jsonify(
            {"success": False, "message": "Data JSON tidak valid."}
            ), 400

    code: str | None = data.get("voucher_code")
    subtotal: Any = data.get("subtotal")
    logger.debug(
        f"Mencoba menerapkan kode voucher: {code} untuk subtotal: {subtotal}"
    )
    
    if not code or subtotal is None:
        logger.warning(
            f"Permintaan penerapan voucher tidak valid. "
            f"Kode: {code}, Subtotal: {subtotal}"
        )
        return jsonify(
            {"success": False, "message": "Kode voucher dan subtotal diperlukan."}
            ), 400

    try:
        subtotal_float: float = float(subtotal)
        result: Dict[str, Any] = (
            discount_service.validate_and_calculate_voucher(
                code, subtotal_float
            )
        )

        if result["success"]:
            logger.info(
                f"Voucher '{code}' berhasil diterapkan. "
                f"Diskon: {result['discount_amount']}"
            )
            return jsonify(result), 200
        
        else:
            logger.info(
                f"Penerapan voucher '{code}' gagal. "
                f"Alasan: {result['message']}"
            )
            return jsonify(
                {"success": False, "message": result["message"]}
                ), 400

    except ValueError:
        logger.error(f"Format subtotal tidak valid: {subtotal}", exc_info=True)
        return jsonify(
            {"success": False, "message": "Format subtotal tidak valid."}
            ), 400
    
    except (ValidationError, DatabaseException, ServiceLogicError) as e:
        logger.error(
            f"Error caught applying voucher '{code}': {e}", exc_info=True
        )
        status_code = 500
        if isinstance(e, ValidationError):
            status_code = 400
        return jsonify({"success": False, "message": str(e)}), status_code
    
    except Exception as e:
        logger.error(
            f"Kesalahan tak terduga saat menerapkan voucher '{code}': {e}",
            exc_info=True,
        )
        return jsonify(
            {"success": False, "message": "Gagal memvalidasi voucher."}
            ), 500