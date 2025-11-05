from typing import Any, Dict, Optional, Union

from flask import (
    flash, redirect, render_template,
    request, session, url_for
)
import mysql.connector
from werkzeug.wrappers import Response

from app.core.db import get_content, get_db_connection
from app.exceptions.api_exceptions import AuthError
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.services.auth.authentication_service import authentication_service
from app.utils.logging_utils import get_logger

from . import auth_bp

logger = get_logger(__name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login() -> Union[Response, str]:
    if "user_id" in session:
        logger.info(
            f"Pengguna {session['username']} (ID: {session['user_id']}) "
            "sudah login, mengarahkan ulang."
        )
        return redirect(url_for("product.products_page"))

    next_url: Optional[str] = request.args.get("next")
    guest_session_id: Any = session.get("session_id")
    logger.debug(
        f"Halaman login diakses. URL berikutnya: {next_url}, "
        f"ID Sesi Tamu: {guest_session_id}"
    )

    if request.method == "POST":
        username_or_email: Optional[str] = request.form.get("username")
        password: Optional[str] = request.form.get("password")
        logger.info(f"Percobaan login untuk: {username_or_email}")

        if not username_or_email or not password:
            flash("Username/Email dan password harus diisi.", "danger")
            return redirect(url_for("auth.login", next=next_url))

        try:
            user: Dict[str, Any] = (
                authentication_service.verify_user_login(username_or_email, password)
            )

            user_id: int = user["id"]
            logger.info(
                f"Login berhasil untuk pengguna: {user['username']} (ID: {user_id}), "
                f"Admin: {bool(user['is_admin'])}"
            )

            session.clear()
            session["user_id"] = user_id
            session["username"] = user["username"]
            session["is_admin"] = bool(user["is_admin"])
            session["just_logged_in"] = True

            if guest_session_id:
                conn: Optional[mysql.connector.MySQLConnection] = None
                cursor: Optional[mysql.connector.cursor.MySQLCursor] = None

                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    logger.debug(
                        "Mencoba memindahkan data penahanan stok dari "
                        f"sesi {guest_session_id} ke pengguna {user_id}"
                    )
                    
                    cursor.execute(
                        """
                        UPDATE stock_holds
                        SET user_id = %s, session_id = NULL
                        WHERE session_id = %s AND user_id IS NULL
                        """,
                        (user_id, guest_session_id),
                    )

                    conn.commit()

                    if cursor.rowcount > 0:
                        logger.info(
                            f"Berhasil memindahkan {cursor.rowcount} "
                            f"data penahanan stok untuk pengguna {user_id}"
                        )
                        flash("Keranjang tamu Anda telah digabungkan.", "info")
                    else:
                        logger.info(
                            "Tidak ada data penahanan stok yang dipindahkan "
                            f"untuk sesi {guest_session_id}"
                        )

                except mysql.connector.Error as db_e:
                    if conn and conn.is_connected():
                        conn.rollback()
                    logger.error(
                        "Terjadi kesalahan saat memindahkan data penahanan "
                        f"stok saat login untuk pengguna {user_id}: {db_e}",
                        exc_info=True,
                    )
                    flash("Gagal menggabungkan keranjang tamu.", "warning")

                finally:
                    if cursor:
                        cursor.close()
                    if conn and conn.is_connected():
                        conn.close()

            if session["is_admin"]:
                flash("Login admin berhasil!", "success")
                return redirect(url_for("admin.admin_dashboard"))

            flash("Anda berhasil login!", "success")
            redirect_target: str = next_url or url_for(
                "product.products_page"
            )
            logger.info(
                f"Mengarahkan pengguna {user['username']} ke {redirect_target}"
            )
            return redirect(redirect_target)

        except AuthError as ae:
            logger.warning(f"Login gagal untuk: {username_or_email} - {ae}")
            flash(str(ae), "danger")

        except (DatabaseException, ServiceLogicError) as e:
            logger.error(
                f"Kesalahan service/DB saat login untuk {username_or_email}: {e}",
                exc_info=True,
            )
            flash("Terjadi kesalahan saat mencoba login.", "danger")

        except Exception as e:
            logger.error(
                f"Kesalahan tak terduga saat login untuk {username_or_email}: {e}",
                exc_info=True,
            )
            flash("Terjadi kesalahan tak terduga.", "danger")

        return redirect(url_for("auth.login", next=next_url))

    return render_template(
        "auth/login.html", content=get_content(), hide_navbar=True
    )