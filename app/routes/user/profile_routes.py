from typing import Any, Dict, List, Optional, Tuple, Union

import mysql.connector
from flask import (
    Response, flash, jsonify, redirect,
    render_template, request, session, url_for
)
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursorDict

from app.core.db import get_content, get_db_connection
from app.exceptions.api_exceptions import AuthError, ValidationError
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
)
from app.exceptions.service_exceptions import ServiceLogicError
from app.services.orders.voucher_service import voucher_service
from app.services.users.user_service import user_service
from app.utils.logging_utils import get_logger
from app.utils.route_decorators import login_required

from . import user_bp

logger = get_logger(__name__)


@user_bp.route("/profile")
@login_required
def user_profile() -> Union[str, Response, Tuple[Response, int]]:
    user_id: int = session["user_id"]
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    logger.debug(
        f"Mengakses halaman profil (AJAX: {is_ajax}) "
        f"untuk ID pengguna: {user_id}"
    )
    page_title = (
        f"Profil Saya - {get_content().get('app_name', 'App')}"
    )
    conn: Optional[MySQLConnection] = None
    cursor: Optional[MySQLCursorDict] = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user: Optional[Dict[str, Any]] = cursor.fetchone()
        if not user:
            logger.error(
                f"Kesalahan akses profil: ID pengguna {user_id} tidak ditemukan."
            )
            session.clear()
            message = "Sesi Anda tidak valid, silakan login kembali."
            if is_ajax:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": message,
                            "redirect_url": url_for("auth.login"),
                        }
                    ),
                    401,
                )
            flash(message, "danger")
            return redirect(url_for("auth.login"))

        cursor.execute(
            "SELECT * FROM orders WHERE user_id = %s ORDER BY order_date DESC",
            (user_id,),
        )
        orders: List[Dict[str, Any]] = cursor.fetchall()

        my_vouchers: List[Dict[str, Any]] = (
            voucher_service.get_available_vouchers_for_user(user_id)
        )
        
        current_subscription = user_service.get_active_subscription(user_id, conn)

        logger.info(
            f"Berhasil mengambil profil, {len(orders)} pesanan, "
            f"dan {len(my_vouchers)} voucher untuk ID pengguna: {user_id}"
        )
        logger.debug(
            f"Status langganan aktif pengguna {user_id}: {bool(current_subscription)}"
            )

        render_args = {
            "user": user,
            "orders": orders,
            "my_vouchers": my_vouchers,
            "current_subscription": current_subscription,
            "content": get_content(),
        }

        if is_ajax:
            html = render_template(
                "partials/user/_user_profile.html", **render_args
            )
            return jsonify(
                {"success": True, "html": html, "page_title": page_title}
            )
        else:
            return render_template("user/user_profile.html", **render_args)

    except mysql.connector.Error as db_err:
        logger.error(
            f"Kesalahan database saat mengambil profil pengguna {user_id}: "
            f"{db_err}",
            exc_info=True,
        )
        message = "Gagal memuat profil Anda karena kesalahan database."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        flash(message, "danger")

    except Exception as e:
        logger.error(
            f"Kesalahan tak terduga saat mengambil profil pengguna {user_id}: {e}",
            exc_info=True,
        )
        message = "Gagal memuat profil Anda."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        flash(message, "danger")

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

    return redirect(url_for("product.index"))


@user_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile() -> Union[str, Response, Tuple[Response, int]]:
    user_id: int = session["user_id"]
    is_ajax: bool = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method == "POST":
        action: Optional[str] = request.form.get("form_action")
        logger.debug(
            f"Memproses permintaan POST (AJAX: {is_ajax}) edit profil "
            f"pengguna {user_id}. Aksi: {action}"
        )
        result: Dict[str, Any] = {}
        status_code: int = 200

        try:
            if action == "update_info":
                username: str = request.form["username"]
                email: str = request.form["email"]
                logger.info(
                    f"Memanggil service update_user_info pengguna {user_id}. "
                    f"Nama baru: {username}, Email baru: {email}"
                )
                result = user_service.update_user_info(
                    user_id, username, email
                )
                if result.get("success"):
                    session["username"] = username
                    result["data"] = {"username": username, "email": email}
                else:
                    status_code = 400

            elif action == "change_password":
                current_password: str = request.form["current_password"]
                new_password: str = request.form["new_password"]
                logger.info(
                    "Memanggil service change_user_password "
                    f"pengguna {user_id}."
                )
                result = user_service.change_user_password(
                    user_id, current_password, new_password
                )
                if not result.get("success"):
                    status_code = 400

            elif action == "update_address":
                address_data: Dict[str, str] = {
                    "full_name": request.form["full_name"],
                    "phone": request.form["phone"],
                    "address1": request.form["address_line_1"],
                    "address2": request.form.get("address_line_2", ""),
                    "city": request.form["city"],
                    "province": request.form["province"],
                    "postal_code": request.form["postal_code"],
                }
                logger.info(
                    "Memanggil service update_user_address "
                    f"pengguna {user_id}."
                )
                result = user_service.update_user_address(
                    user_id, address_data
                )
                if result.get("success"):
                    result["data"] = request.form.to_dict()
                else:
                    status_code = 400

            else:
                logger.warning(
                    f"Aksi tidak valid '{action}' diterima "
                    f"untuk pengguna {user_id}."
                )
                raise ValidationError("Aksi tidak dikenal.")

        except (ValidationError, AuthError) as user_error:
            logger.warning(
                f"Kesalahan memproses edit profil '{action}' "
                f"pengguna {user_id}: {user_error}"
            )
            result = {"success": False, "message": str(user_error)}
            status_code = 401 if isinstance(user_error, AuthError) else 400

        except (DatabaseException, ServiceLogicError) as service_err:
            logger.error(
                f"Kesalahan Service/DB memproses edit profil '{action}' "
                f"pengguna {user_id}: {service_err}",
                exc_info=True,
            )
            result = {"success": False, "message": "Terjadi kesalahan server."}
            status_code = 500

        except Exception as e:
            logger.error(
                f"Kesalahan tak terduga memproses edit profil '{action}' "
                f"pengguna {user_id}: {e}",
                exc_info=True,
            )
            result = {"success": False, "message": "Terjadi kesalahan server."}
            status_code = 500

        logger.debug(
            f"Mengirim respons JSON POST. Aksi: '{action}', "
            f"Berhasil: {result.get('success')}"
        )
        return jsonify(result), status_code

    logger.debug(
        f"Mengakses halaman edit profil (GET) (AJAX: {is_ajax}) "
        f"untuk ID pengguna: {user_id}"
    )
    page_title = (
        f"Edit Profil - {get_content().get('app_name', 'App')}"
    )

    try:
        user = user_service.get_user_by_id(user_id)
        if not user:
            raise RecordNotFoundError(f"Pengguna {user_id} tidak ditemukan")

        render_args = {"user": user, "content": get_content()}

        if is_ajax:
            html = render_template(
                "partials/user/_profile_editor.html", **render_args
            )
            return jsonify(
                {"success": True, "html": html, "page_title": page_title}
            )
        else:
            return render_template("user/profile_editor.html", **render_args)

    except RecordNotFoundError:
        logger.error(
            f"Kesalahan akses edit profil: ID pengguna {user_id} tidak ditemukan."
        )
        session.clear()
        message = "Sesi Anda tidak valid, silakan login kembali."
        if is_ajax:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": message,
                        "redirect_url": url_for("auth.login"),
                    }
                ),
                404,
            )
        flash(message, "danger")
        return redirect(url_for("auth.login"))

    except (DatabaseException, ServiceLogicError) as e:
        logger.error(
            f"Kesalahan saat memuat edit profil pengguna {user_id}: {e}",
            exc_info=True,
        )
        message = "Gagal memuat halaman edit profil."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        flash(message, "danger")
        return redirect(url_for("user.user_profile"))

    except Exception as e:
        logger.error(
            f"Kesalahan tak terduga saat memuat edit profil pengguna {user_id}: {e}",
            exc_info=True,
        )
        message = "Gagal memuat halaman edit profil."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        flash(message, "danger")
        return redirect(url_for("user.user_profile"))