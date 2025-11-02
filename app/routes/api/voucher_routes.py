from typing import Any, Dict, Tuple, Optional

from flask import Response, jsonify, request, session

from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.services.orders.discount_service import discount_service
from app.services.orders.voucher_service import voucher_service
from app.utils.logging_utils import get_logger
from app.utils.route_decorators import login_required

from . import api_bp

logger = get_logger(__name__)


@api_bp.route("/apply-voucher", methods=["POST"])
def apply_voucher() -> Tuple[Response, int]:
    
    data: Dict[str, Any] | None = request.get_json()
    if data is None:
        return jsonify(
            {"success": False, "message": "Data JSON tidak valid."}
        ), 400

    user_id: Optional[int] = session.get("user_id")
    code: str | None = data.get("voucher_code")
    user_voucher_id: Any = data.get("user_voucher_id")
    subtotal: Any = data.get("subtotal")

    if subtotal is None:
        return jsonify(
            {"success": False, "message": "Subtotal diperlukan."}
        ), 400

    if not code and not (user_id and user_voucher_id):
        return jsonify(
            {"success": False, "message": "Kode voucher atau ID voucher diperlukan."}
        ), 400

    try:
        subtotal_float: float = float(subtotal)
        result: Dict[str, Any] = {}

        if user_id and user_voucher_id:
            logger.debug(
                f"Mencoba menerapkan user_voucher_id: {user_voucher_id} "
                f"untuk user {user_id}"
            )
            result = discount_service.validate_and_calculate_by_id(
                user_id, int(user_voucher_id), subtotal_float
            )
        elif code:
            logger.debug(
                f"Mencoba menerapkan kode voucher: {code} "
                f"untuk subtotal: {subtotal}"
            )
            result = discount_service.validate_and_calculate_by_code(
                code, subtotal_float
            )
        else:
            return jsonify(
                {"success": False, "message": "Input tidak valid."}
            ), 400

        if result["success"]:
            logger.info(
                f"Voucher '{result.get('code')}' berhasil diterapkan. "
                f"Diskon: {result['discount_amount']}"
            )
            return jsonify(result), 200
        else:
            logger.info(
                f"Penerapan voucher gagal. Alasan: {result['message']}"
            )
            return jsonify(
                {"success": False, "message": result["message"]}
            ), 400

    except ValueError:
        logger.error(f"Format input tidak valid: {subtotal}", exc_info=True)
        return jsonify(
            {"success": False, "message": "Format input tidak valid."}
        ), 400
    
    except (ValidationError, DatabaseException, ServiceLogicError) as e:
        logger.error(f"Error caught applying voucher: {e}", exc_info=True)
        status_code = 500
        if isinstance(e, ValidationError):
            status_code = 400
        return jsonify(
            {"success": False, "message": str(e)}
            ), status_code
    
    except Exception as e:
        logger.error(
            f"Kesalahan tak terduga saat menerapkan voucher: {e}",
            exc_info=True,
        )
        return jsonify(
            {"success": False, "message": "Gagal memvalidasi voucher."}
        ), 500


@api_bp.route("/my-vouchers", methods=["GET"])
@login_required
def get_my_vouchers() -> Tuple[Response, int]:

    user_id: Optional[int] = session.get("user_id")
    if not user_id:
        return jsonify(
            {"success": False, "message": "Otentikasi diperlukan."}
        ), 401

    try:
        vouchers = voucher_service.get_available_vouchers_for_user(user_id)
        return jsonify(
            {"success": True, "vouchers": vouchers}
            ), 200
    
    except (DatabaseException, ServiceLogicError) as e:
        logger.error(f"Gagal mengambil voucher pengguna {user_id}: {e}")
        return jsonify(
            {"success": False, "message": "Gagal mengambil voucher Anda."}
        ), 500


@api_bp.route("/claim-voucher", methods=["POST"])
@login_required
def claim_voucher() -> Tuple[Response, int]:

    user_id: Optional[int] = session.get("user_id")
    if not user_id:
        return jsonify(
            {"success": False, "message": "Otentikasi diperlukan."}
        ), 401

    data: Dict[str, Any] | None = request.get_json()
    code: str | None = data.get("voucher_code") if data else None

    if not code:
        return jsonify(
            {"success": False, "message": "Kode voucher diperlukan."}
        ), 400

    try:
        result = voucher_service.claim_voucher_by_code(user_id, code)
        status_code = 200 if result["success"] else 400
        return jsonify(result), status_code
    
    except (DatabaseException, ServiceLogicError) as e:
        logger.error(f"Gagal klaim voucher {code} untuk {user_id}: {e}")
        return jsonify(
            {"success": False, "message": "Gagal mengklaim voucher."}
        ), 500