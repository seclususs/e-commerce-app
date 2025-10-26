from typing import Tuple

from flask import Response, jsonify, request

from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.services.utils.validation_service import validation_service
from app.utils.logging_utils import get_logger

from . import api_bp

logger = get_logger(__name__)


@api_bp.route("/validate/username", methods=["POST"])
def validate_username() -> Response:
    username: str | None = request.json.get("username")
    logger.debug(f"API: Memvalidasi username: {username}")

    if not username:
        logger.warning("API: Validasi gagal: kolom username kosong.")
        raise ValidationError("Username tidak boleh kosong.")

    try:
        is_available: bool
        message: str
        is_available, message = (
            validation_service.validate_username_availability(username)
        )
        logger.info(f"API: Hasil validasi username '{username}': {message}")
        return jsonify({"available": is_available, "message": message})
    
    except (DatabaseException, ServiceLogicError) as e:
        logger.error(
            f"API: Terjadi kesalahan saat memvalidasi username '{username}': {e}",
            exc_info=True,
        )
        raise e
    
    except Exception as e:
        logger.error(
            f"API: Kesalahan tak terduga saat memvalidasi username '{username}': {e}",
            exc_info=True,
        )
        raise ServiceLogicError("Gagal memeriksa ketersediaan username.")


@api_bp.route("/validate/email", methods=["POST"])
def validate_email() -> Response:
    email: str | None = request.json.get("email")
    logger.debug(f"API: Memvalidasi email: {email}")

    if not email:
        logger.warning("API: Validasi gagal: kolom email kosong.")
        raise ValidationError("Email tidak boleh kosong.")

    try:
        is_available: bool
        message: str
        is_available, message = validation_service.validate_email_availability(
            email
        )
        logger.info(f"API: Hasil validasi email '{email}': {message}")
        return jsonify({"available": is_available, "message": message})
    
    except (DatabaseException, ServiceLogicError) as e:
        logger.error(
            f"API: Terjadi kesalahan saat memvalidasi email '{email}': {e}",
            exc_info=True,
        )
        raise e
    
    except Exception as e:
        logger.error(
            f"API: Kesalahan tak terduga saat memvalidasi email '{email}': {e}",
            exc_info=True,
        )
        raise ServiceLogicError("Gagal memeriksa ketersediaan email.")