from typing import Any, Dict, Tuple

from flask import Response, current_app, jsonify, request

from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.services.utils.scheduler_service import scheduler_service
from app.utils.logging_utils import get_logger

from . import api_bp

logger = get_logger(__name__)


@api_bp.route("/admin/run-scheduler-jobs", methods=["POST"])
def run_scheduler_jobs() -> Tuple[Response, int]:
    secret_key: str = current_app.config["SECRET_KEY"]
    auth_header: str | None = request.headers.get("X-API-Key")
    logger.info(
        "Menerima permintaan untuk menjalankan tugas scheduler. "
        f"Header otentikasi ada: {'Ya' if auth_header else 'Tidak'}"
    )

    if auth_header != secret_key:
        logger.warning("Percobaan tidak sah untuk menjalankan tugas scheduler.")
        return jsonify({"success": False, "message": "Tidak diizinkan"}), 401

    try:
        logger.info("Menjalankan layanan scheduler: cancel_expired_pending_orders")
        cancel_result: Dict[str, Any] = (
            scheduler_service.cancel_expired_pending_orders()
        )
        logger.info(f"Tugas pembatalan selesai. Hasil: {cancel_result}")
        
        logger.info("Menjalankan layanan scheduler: grant_segmented_vouchers")
        segment_result: Dict[str, Any] = (
            scheduler_service.grant_segmented_vouchers()
        )
        logger.info(f"Tugas voucher segmen selesai. Hasil: {segment_result}")

        cancel_count = cancel_result.get("cancelled_count", 0)
        grant_count = segment_result.get("granted_count", 0)
        
        final_success = cancel_result["success"] and segment_result["success"]
        
        message = (
            f"Tugas selesai. {cancel_count} pesanan dibatalkan. "
            f"{grant_count} voucher top spender diberikan."
        )

        return (
            jsonify({"success": final_success, "message": message}),
            200 if final_success else 500
        )
    
    except (DatabaseException, ServiceLogicError) as e:
        logger.error(
            f"Error caught running scheduler manually: {e}", exc_info=True
        )
        return (
            jsonify(
                {"success": False, "message": "Terjadi kesalahan server."}
            ), 500
        )
    
    except Exception as e:
        logger.error(
            "Terjadi kesalahan tak terduga saat menjalankan tugas scheduler "
            f"melalui API: {e}",
            exc_info=True,
        )
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Terjadi kesalahan internal saat menjalankan tugas scheduler.",
                }
            ),
            500,
        )