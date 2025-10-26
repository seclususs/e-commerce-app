from typing import Any

from flask import flash, redirect, session, url_for
from werkzeug.wrappers import Response

from app.utils.logging_utils import get_logger

from . import auth_bp

logger = get_logger(__name__)


@auth_bp.route("/logout")
def logout() -> Response:
    user_id: Any = session.get("user_id")
    username: Any = session.get("username")

    logger.info(f"Proses logout dimulai. Pengguna: {username} (ID: {user_id})")
    session.clear()
    flash("Anda telah logout.", "success")
    logger.info(f"Pengguna {username} (ID: {user_id}) berhasil logout.")
    return redirect(url_for("product.index"))