from typing import Any, Dict, Tuple

from flask import Blueprint, Response, current_app, jsonify, request

from app.exceptions.api_exceptions import AuthError
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.services.utils.scheduler_service import scheduler_service
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)

scheduler_api_bp: Blueprint = Blueprint("scheduler_api", __name__)


@scheduler_api_bp.route("/admin/run-scheduler-jobs", methods=["POST"])
def run_scheduler_jobs() -> Tuple[Response, int]:
    secret_key: str = current_app.config["SECRET_KEY"]
    auth_header: str | None = request.headers.get("X-API-Key")
    logger.info(
        "Menerima permintaan untuk menjalankan tugas scheduler. "
        f"Header otentikasi ada: {'Ya' if auth_header else 'Tidak'}"
    )

    if auth_header != secret_key:
        logger.warning("Percobaan tidak sah untuk menjalankan tugas scheduler.")
        raise AuthError("Tidak diizinkan")

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
        raise e
    
    except Exception as e:
        logger.error(
            "Terjadi kesalahan tak terduga saat menjalankan tugas scheduler "
            f"melalui API: {e}",
            exc_info=True,
        )
        raise ServiceLogicError(
            "Terjadi kesalahan internal saat menjalankan tugas scheduler."
        )