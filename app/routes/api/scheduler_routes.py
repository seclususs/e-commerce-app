from typing import Any, Dict, Tuple

from flask import Blueprint, Response, current_app, jsonify, request

from app.exceptions.api_exceptions import AuthError
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
        result: Dict[str, Any] = (
            scheduler_service.cancel_expired_pending_orders()
        )
        logger.info(f"Tugas scheduler selesai dijalankan. Hasil: {result}")
        return jsonify(result), 200 if result["success"] else 500
    
    except (DatabaseException, ServiceLogicError) as e:
        logger.error(
            f"Error caught running scheduler manually: {e}", exc_info=True
        )
        return jsonify({"success": False, "message": "Terjadi kesalahan server."}), 500
    
    except Exception as e:
        logger.error(
            "Terjadi kesalahan tak terduga saat menjalankan tugas scheduler "
            f"melalui API: {e}",
            exc_info=True,
        )
        return jsonify(
            {
                "success": False,
                "message": "Terjadi kesalahan internal saat menjalankan tugas scheduler.",
            }
        ), 500