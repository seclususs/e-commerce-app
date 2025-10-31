from typing import Optional, Union

from flask import (
    flash, jsonify, redirect,
    render_template, request,
    url_for
)
from werkzeug.wrappers import Response

from app.core.db import get_content
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.service_exceptions import ServiceLogicError
from app.services.auth.password_reset_service import password_reset_service
from app.utils.logging_utils import get_logger

from . import auth_bp

logger = get_logger(__name__)


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password() -> Union[Response, str]:
    if request.method == "POST":
        email: Optional[str] = request.form.get("email")
        logger.info(f"Permintaan reset password untuk email: {email}")
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

        try:
            if not email:
                raise ValidationError("Email harus diisi.")

            password_reset_service.handle_password_reset_request(email)
            message: str = (
                "Jika email terdaftar, link reset password telah dikirim."
            )
            logger.info(f"Simulasi reset password dimulai untuk email: {email}")
            
            if is_ajax:
                logger.debug(
                    "Merespons dengan JSON untuk permintaan reset "
                    "password melalui AJAX."
                )
                return jsonify({"success": True, "message": message})

            flash(f"SIMULASI: {message}", "success")
            return redirect(url_for("auth.login"))
        
        except ValidationError as ve:
            logger.warning(f"Validasi gagal untuk reset password: {ve}")
            if is_ajax:
                return jsonify({"success": False, "message": str(ve)}), 400
            flash(str(ve), "danger")
            return redirect(url_for("auth.forgot_password"))

        except ServiceLogicError as sle:
            logger.error(
                f"Kesalahan service saat reset password untuk {email}: {sle}",
                exc_info=True,
            )
            if is_ajax:
                raise sle
            flash("Terjadi kesalahan saat memproses permintaan.", "danger")
            return redirect(url_for("auth.forgot_password"))
        
        except Exception as e:
            logger.error(
                "Kesalahan tak terduga saat menangani permintaan "
                f"reset password untuk email {email}: {e}",
                exc_info=True,
            )
            if is_ajax:
                raise ServiceLogicError(
                    "Terjadi kesalahan server saat memproses permintaan."
                )
            flash(
                "Terjadi kesalahan saat memproses permintaan reset password.",
                "danger",
            )
            return redirect(url_for("auth.forgot_password"))

    logger.debug("Menampilkan halaman lupa password.")
    return render_template(
        "auth/forgot_password.html", content=get_content(), hide_navbar=True
    )