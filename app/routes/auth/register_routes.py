import json
from typing import Any, Dict, Optional, Union

from flask import (
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
import mysql.connector
from werkzeug.wrappers import Response

from app.core.db import get_content, get_db_connection
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.services.auth.registration_service import registration_service
from app.utils.logging_utils import get_logger

from . import auth_bp

logger = get_logger(__name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register() -> Union[Response, str]:
    if "user_id" in session:
        logger.info(
            f"Pengguna {session['username']} sudah login, "
            "mengarahkan ulang dari halaman registrasi."
        )
        return redirect(url_for("product.products_page"))

    if request.method == "POST":
        username: Optional[str] = request.form.get("username")
        email: Optional[str] = request.form.get("email")
        password: Optional[str] = request.form.get("password")
        logger.info(
            f"Percobaan registrasi untuk username: {username}, email: {email}"
        )
        
        try:
            if not username or not email or not password:
                raise ValidationError(
                    "Username, email, dan password harus diisi."
                )

            new_user: Dict[str, Any] = (
                registration_service.register_new_user(
                    username, email, password
                )
            )
            session.clear()
            session["user_id"] = new_user["id"]
            session["username"] = new_user["username"]
            session["is_admin"] = bool(new_user["is_admin"])
            logger.info(
                f"Registrasi berhasil untuk pengguna: {username} "
                f"(ID: {new_user['id']}). Melakukan login otomatis."
            )
            flash("Registrasi berhasil! Selamat datang.", "success")
            return redirect(url_for("product.products_page"))

        except ValidationError as ve:
            logger.warning(
                f"Registrasi gagal untuk username: {username}. Validasi: {ve}"
            )
            flash(str(ve), "danger")

        except (DatabaseException, ServiceLogicError) as e:
            logger.error(
                "Kesalahan service/DB saat registrasi untuk "
                f"username {username}: {e}",
                exc_info=True,
            )
            flash("Terjadi kesalahan saat pendaftaran.", "danger")

        except Exception as e:
            logger.error(
                "Kesalahan tak terduga saat registrasi untuk "
                f"username {username}: {e}",
                exc_info=True,
            )
            flash("Terjadi kesalahan tak terduga saat pendaftaran.", "danger")

        return redirect(url_for("auth.register"))

    logger.debug("Menampilkan halaman registrasi.")
    return render_template(
        "auth/register.html", content=get_content(), hide_navbar=True
    )


@auth_bp.route("/register_from_order", methods=["POST"])
def register_from_order() -> Response:
    order_details_str: Optional[str] = request.form.get("order_details")
    password: Optional[str] = request.form.get("password")
    order_id: Optional[str] = request.form.get("order_id")
    logger.info(
        f"Mencoba mendaftarkan pengguna dari pesanan tamu dengan ID: {order_id}"
    )

    if not order_details_str or not password or not order_id:
        logger.warning(
            f"Registrasi dari pesanan gagal: Data tidak lengkap. "
            f"ID Pesanan: {order_id}"
        )
        flash("Data pendaftaran tidak lengkap.", "danger")
        return redirect(url_for("purchase.order_success"))

    try:
        order_details: Dict[str, Any] = json.loads(order_details_str)
        email: Optional[str] = order_details.get("email")

        if not email:
            raise ValidationError("Email tidak ditemukan dalam detail pesanan")

        logger.debug(
            f"Detail pesanan berhasil dimuat untuk registrasi. Email: {email}"
        )
        new_user: Dict[str, Any] = (
            registration_service.register_guest_user(order_details, password)
        )
        logger.info(
            f"Pengguna tamu berhasil didaftarkan dari pesanan {order_id}. "
            f"ID Pengguna Baru: {new_user['id']}, "
            f"Username: {new_user['username']}"
        )
        session.clear()
        session["user_id"] = new_user["id"]
        session["username"] = new_user["username"]
        session["is_admin"] = bool(new_user["is_admin"])

        conn: Optional[mysql.connector.MySQLConnection] = None
        cursor: Optional[mysql.connector.cursor.MySQLCursor] = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE orders SET user_id = %s "
                "WHERE id = %s AND user_id IS NULL",
                (new_user["id"], order_id),
            )

            conn.commit()

            if cursor.rowcount > 0:
                logger.info(
                    f"Pesanan {order_id} berhasil dikaitkan dengan "
                    f"pengguna baru {new_user['id']}."
                )

            else:
                logger.warning(
                    f"Gagal mengaitkan pesanan {order_id} dengan "
                    f"pengguna baru {new_user['id']}. Pesanan mungkin "
                    f"sudah memiliki ID pengguna atau ID tidak valid."
                )

        except Exception as db_e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan saat mengaitkan pesanan {order_id} "
                f"dengan pengguna {new_user['id']}: {db_e}",
                exc_info=True,
            )
            flash("Gagal mengaitkan pesanan dengan akun baru Anda.", "warning")

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

        flash("Akun berhasil dibuat dan Anda telah login!", "success")
        return redirect(url_for("user.user_profile"))

    except ValidationError as ve:
        logger.warning(
            "Gagal mendaftarkan pengguna tamu dari pesanan "
            f"{order_id}. Validasi: {ve}"
        )
        flash(str(ve), "danger")
        session["guest_order_details"] = (
            order_details if "order_details" in locals() else None
        )
        session["guest_order_id"] = order_id
        return redirect(url_for("purchase.order_success"))
    
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(
            "Kesalahan saat memproses detail pesanan atau email hilang untuk "
            f"registrasi dari pesanan {order_id}: {e}",
            exc_info=True,
        )
        flash("Data pesanan tidak valid.", "danger")
        return redirect(url_for("purchase.order_success"))
    
    except (DatabaseException, ServiceLogicError) as e:
        logger.error(
            "Kesalahan service/DB saat registrasi dari pesanan "
            f"{order_id}: {e}",
            exc_info=True,
        )
        flash("Terjadi kesalahan saat membuat akun.", "danger")
        session["guest_order_details"] = (
            order_details if "order_details" in locals() else None
        )
        session["guest_order_id"] = order_id
        return redirect(url_for("purchase.order_success"))
    
    except Exception as e:
        logger.error(
            "Kesalahan tak terduga saat registrasi dari pesanan "
            f"{order_id}: {e}",
            exc_info=True,
        )
        flash("Terjadi kesalahan server saat membuat akun.", "danger")
        session["guest_order_details"] = (
            order_details if "order_details" in locals() else None
        )
        session["guest_order_id"] = order_id
        return redirect(url_for("purchase.order_success"))