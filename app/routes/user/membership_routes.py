from typing import Optional, Union, Tuple

from flask import (
    Response, flash, jsonify, redirect,
    render_template, request, session, url_for
)

from app.core.db import get_content, get_db_connection
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
)
from app.exceptions.service_exceptions import (
    ServiceLogicError, InvalidOperationError
)
from app.services.auth.registration_service import registration_service
from app.services.member.membership_service import membership_service
from app.services.users.user_service import user_service
from app.utils.logging_utils import get_logger
from app.utils.route_decorators import login_required

from . import user_bp

logger = get_logger(__name__)


@user_bp.route("/membership", methods=["GET", "POST"])
def membership_page() -> Union[str, Response, Tuple[Response, int]]:
    user_id: Optional[int] = session.get("user_id")
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    logger.debug(
        f"Mengakses halaman membership (AJAX: {is_ajax}) "
        f"untuk ID pengguna: {user_id or 'Tamu'}"
    )
    
    if request.method == "POST" and user_id:
        action = request.form.get("action")
        membership_id = request.form.get("membership_id")
        
        if not membership_id:
            return jsonify(
                {"success": False, "message": "Membership ID diperlukan."}
                ), 400

        try:
            membership_id_int = int(membership_id)
            result = {}
            if action == "subscribe":
                logger.info(
                    f"Pengguna {user_id} mencoba berlangganan paket {membership_id_int}"
                    )
                result = membership_service.subscribe_to_plan(
                    user_id, membership_id_int
                )
            elif action == "upgrade":
                logger.info(
                    f"Pengguna {user_id} mencoba upgrade ke paket {membership_id_int}"
                    )
                result = membership_service.upgrade_subscription(
                    user_id, membership_id_int
                )
            else:
                return jsonify(
                    {"success": False, "message": "Aksi tidak valid."}
                    ), 400
            
            if result["success"] and result.get("order_id"):
                result["redirect_url"] = url_for(
                    "purchase.payment_page", order_id=result["order_id"]
                    )
                return jsonify(result), 200
            else:
                status_code = (
                    404 if "tidak ditemukan" in result.get("message", "")
                    else 400
                )
                return jsonify(result), status_code

        except (InvalidOperationError, RecordNotFoundError, ValidationError) as e:
            return jsonify(
                {"success": False, "message": str(e)}
                ), 400
        
        except (DatabaseException, ServiceLogicError) as e:
            logger.error(f"Error saat POST /membership: {e}", exc_info=True)
            return jsonify(
                {"success": False, "message": "Kesalahan server."}
                ), 500
        
        except Exception as e:
            logger.error(f"Error tak terduga saat POST /membership: {e}", exc_info=True)
            return jsonify(
                {"success": False, "message": "Kesalahan server."}
                ), 500

    page_title = f"Keanggotaan VIP - {get_content().get('app_name', 'App')}"
    try:
        all_memberships = (
            membership_service.get_all_active_memberships()
        )
        current_subscription = None
        if user_id:
            current_subscription = user_service.get_active_subscription(user_id)

        render_args = {
            "all_memberships": all_memberships,
            "current_subscription": current_subscription,
            "content": get_content(),
        }

        if is_ajax:
            html = render_template(
                "partials/public/_membership.html", **render_args
            )
            return jsonify(
                {"success": True, "html": html, "page_title": page_title}
            )
        else:
            return render_template("public/membership.html", **render_args)

    except (DatabaseException, ServiceLogicError) as e:
        logger.error(
            f"Kesalahan database/layanan saat mengambil halaman membership: {e}",
            exc_info=True,
        )
        message = "Gagal memuat halaman keanggotaan."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        flash(message, "danger")
        return redirect(
            url_for("user.user_profile") if user_id else url_for("product.index")
            )
    
    except Exception as e:
        logger.error(
            f"Kesalahan tak terduga saat mengambil halaman membership: {e}",
            exc_info=True,
        )
        message = "Gagal memuat halaman keanggotaan."
        if is_ajax:
            return jsonify(
                {"success": False, "message": message}
                ), 500
        flash(message, "danger")
        return redirect(
            url_for("user.user_profile") if user_id else url_for("product.index")
            )


@user_bp.route("/subscribe/guest/<int:membership_id>", methods=["GET"])
def guest_subscribe_page(membership_id: int) -> Union[str, Response]:
    if "user_id" in session:
        return redirect(url_for("user.membership_page"))

    conn = None
    try:
        conn = get_db_connection()
        membership = membership_service.membership_repository.find_membership_by_id(
            conn, membership_id
        )
        if not membership or not membership["is_active"]:
            flash("Paket membership tidak ditemukan atau tidak aktif.", "danger")
            return redirect(url_for("user.membership_page"))
        
        return render_template(
            "public/guest_subscribe.html",
            membership=membership,
            content=get_content(),
            hide_navbar=True
        )
    except Exception as e:
        logger.error(
            f"Gagal memuat halaman subscribe tamu untuk paket {membership_id}: {e}",
            exc_info=True
        )
        flash("Gagal memuat halaman pendaftaran.", "danger")
        return redirect(url_for("user.membership_page"))
    finally:
        if conn and conn.is_connected():
            conn.close()


@user_bp.route("/subscribe/guest", methods=["POST"])
def guest_subscribe_submit() -> Response:
    if "user_id" in session:
        return redirect(url_for("user.membership_page"))

    form_data = request.form
    username = form_data.get("username")
    email = form_data.get("email")
    password = form_data.get("password")
    membership_id = form_data.get("membership_id")

    if not all([username, email, password, membership_id]):
        flash("Semua field wajib diisi.", "danger")
        return redirect(
            url_for("user.guest_subscribe_page", membership_id=membership_id)
            )

    try:
        new_user = registration_service.register_new_user(
            username, email, password
        )
        if not new_user:
            raise ServiceLogicError("Gagal mendaftarkan pengguna.")
        
        logger.info(
            f"Pengguna baru {username} (ID: {new_user['id']}) dibuat dari alur subscribe tamu."
            )

        session.clear()
        session["user_id"] = new_user["id"]
        session["username"] = new_user["username"]
        session["is_admin"] = bool(new_user["is_admin"])
        
        subscribe_result = membership_service.subscribe_to_plan(
            new_user["id"], int(membership_id)
        )
        
        if not subscribe_result["success"] or not subscribe_result.get("order_id"):
            logger.warning(
                f"Pengguna {new_user['id']} berhasil daftar TAPI gagal membuat pesanan "
                f"membership {membership_id}: {subscribe_result.get('message')}"
            )
            flash(
                "Akun Anda berhasil dibuat, tetapi gagal mendaftar paket membership. "
                "Silakan coba lagi dari halaman profil Anda.", "warning"
            )
            return redirect(url_for("user.user_profile"))

        logger.info(
            f"Pengguna {new_user['id']} berhasil membuat pesanan membership {subscribe_result['order_id']} "
            "setelah registrasi tamu."
        )
        flash(
            "Selamat! Akun Anda telah dibuat. Silakan selesaikan pembayaran untuk mengaktifkan paket.",
            "success"
        )
        return redirect(
            url_for("purchase.payment_page", order_id=subscribe_result["order_id"])
            )

    except ValidationError as e:
        flash(str(e), "danger")
        return redirect(
            url_for("user.guest_subscribe_page", membership_id=membership_id)
            )
    
    except (DatabaseException, ServiceLogicError) as e:
        logger.error(
            f"Gagal memproses subscribe tamu: {e}", 
            exc_info=True
            )
        flash("Terjadi kesalahan server saat mendaftar.", "danger")
        return redirect(
            url_for("user.guest_subscribe_page", membership_id=membership_id)
            )
    
    except Exception as e:
        logger.error(
            f"Error tak terduga saat subscribe tamu: {e}", 
            exc_info=True
            )
        flash("Terjadi kesalahan tak terduga.", "danger")
        return redirect(
            url_for("user.guest_subscribe_page", membership_id=membership_id)
            )


@user_bp.route("/subscribe/<int:membership_id>", methods=["POST"])
@login_required
def subscribe(membership_id: int) -> Tuple[Response, int]:
    user_id: int = session["user_id"]
    logger.info(
        f"Pengguna {user_id} mencoba berlangganan paket {membership_id}"
        )

    try:
        result = membership_service.subscribe_to_plan(user_id, membership_id)
        if result["success"] and result.get("order_id"):
            result["redirect_url"] = url_for(
                "purchase.payment_page", order_id=result["order_id"]
                )
            return jsonify(result), 200
        else:
            status_code = (
                404 if "tidak ditemukan" in result.get("message", "")
                else 400
            )
            return jsonify(result), status_code

    except (InvalidOperationError, RecordNotFoundError, ValidationError) as e:
        return jsonify(
            {"success": False, "message": str(e)}
            ), 400
    
    except (DatabaseException, ServiceLogicError) as e:
        logger.error(
            f"Error saat subscribe: {e}", 
            exc_info=True
            )
        return jsonify(
            {"success": False, "message": "Kesalahan server."}
            ), 500
    
    except Exception as e:
        logger.error(
            f"Error tak terduga saat subscribe: {e}", 
            exc_info=True
            )
        return jsonify(
            {"success": False, "message": "Kesalahan server."}
            ), 500


@user_bp.route("/upgrade/<int:membership_id>", methods=["POST"])
@login_required
def upgrade(membership_id: int) -> Tuple[Response, int]:
    user_id: int = session["user_id"]
    logger.info(
        f"Pengguna {user_id} mencoba upgrade ke paket {membership_id}"
        )

    try:
        result = membership_service.upgrade_subscription(user_id, membership_id)
        if result["success"] and result.get("order_id"):
            result["redirect_url"] = url_for(
                "purchase.payment_page", order_id=result["order_id"]
                )
            return jsonify(result), 200
        else:
            status_code = (
                404 if "tidak ditemukan" in result.get("message", "")
                else 400
            )
            return jsonify(result), status_code

    except (InvalidOperationError, RecordNotFoundError, ValidationError) as e:
        return jsonify(
            {"success": False, "message": str(e)}
            ), 400
    
    except (DatabaseException, ServiceLogicError) as e:
        logger.error(
            f"Error saat upgrade: {e}", 
            exc_info=True
            )
        return jsonify(
            {"success": False, "message": "Kesalahan server."}
            ), 500
    
    except Exception as e:
        logger.error(
            f"Error tak terduga saat upgrade: {e}", 
            exc_info=True
            )
        return jsonify(
            {"success": False, "message": "Kesalahan server."}
            ), 500