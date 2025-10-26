import logging
import uuid
from typing import Any, Dict, Optional, Union

from flask import (
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for
)
from werkzeug.wrappers import Response as WerkzeugResponse

from app.core.db import get_content
from app.exceptions.database_exceptions import (
    DatabaseException,
    RecordNotFoundError
)
from app.exceptions.service_exceptions import (
    OutOfStockError,
    ServiceLogicError
)
from app.services.orders.cart_service import cart_service
from app.services.orders.checkout_service import checkout_service
from app.services.orders.stock_service import stock_service
from app.services.users.user_service import user_service
from app.utils.logging_utils import get_logger
from app.utils.route_decorators import login_required

from . import purchase_bp

logger = get_logger(__name__)


@purchase_bp.route("/checkout", methods=["GET", "POST"])
def checkout() -> Union[str, WerkzeugResponse]:
    user_id: Optional[int] = session.get("user_id")
    user: Optional[Dict[str, Any]] = None
    user_log_id: str = (
        f"User {user_id}"
        if user_id
        else f"Session {session.get('session_id', 'N/A')}"
    )

    try:
        if user_id:
            user = user_service.get_user_by_id(user_id)

        if "session_id" not in session and not user_id:
            session["session_id"] = str(uuid.uuid4())
            logger.info(
                f"Session_id baru dibuat untuk checkout tamu: {session['session_id']}"
            )

        session_id: Optional[str] = session.get("session_id")

        if request.method == "POST":
            logger.info(
                f"Memproses permintaan POST untuk checkout. {user_log_id}"
            )
            form_data: Dict[str, Any] = request.form.to_dict()
            guest_cart_json: Optional[str] = (
                form_data.get("cart_data") if not user_id else None
            )
            result: Dict[str, Any] = checkout_service.process_checkout(
                user_id, session_id, form_data, guest_cart_json
            )

            if result.get("redirect"):
                if result.get("message") and result.get("flash_category"):
                    flash(result["message"], result["flash_category"])
                return redirect(result["redirect"])
            
            elif not result.get("success"):
                flash(
                    result.get("message", "Terjadi kesalahan."),
                    result.get("flash_category", "danger"),
                )
                return redirect(url_for("purchase.cart_page"))

        logger.debug(f"Mengakses halaman checkout (GET). {user_log_id}")
        stock_hold_expires: Optional[Any] = None

        if user_id:
            cart_details: Dict[str, Any] = (
                cart_service.get_cart_details(user_id)
            )

            if not cart_details or not cart_details.get("items"):
                logger.warning(
                    f"Pengguna {user_id} mengakses checkout dengan keranjang kosong."
                )
                flash(
                    "Keranjang Anda kosong. Silakan tambahkan item terlebih dahulu.",
                    "warning",
                )
                return redirect(url_for("purchase.cart_page"))

            hold_result: Dict[str, Any] = (
                stock_service.hold_stock_for_checkout(
                    user_id, None, cart_details["items"]
                )
            )

            if not hold_result["success"]:
                logger.error(
                    f"Gagal menahan stok untuk pengguna {user_id} saat checkout GET. Alasan: {hold_result['message']}"
                )
                flash(hold_result["message"], "danger")
                return redirect(url_for("purchase.cart_page"))
            
            stock_hold_expires = hold_result.get("expires_at")
            logger.info(
                f"Penahanan stok berhasil untuk pengguna {user_id} saat checkout GET. Kedaluwarsa pada: {stock_hold_expires}"
            )

        else:
            logger.info(
                f"Menampilkan halaman checkout untuk pengguna tamu. ID Sesi: {session_id}. Validasi/penahanan stok akan dilakukan oleh frontend."
            )

        return render_template(
            "purchase/checkout_page.html",
            user=user,
            content=get_content(),
            stock_hold_expires=stock_hold_expires,
        )

    except RecordNotFoundError:
        logger.error(f"Checkout gagal: Pengguna {user_id} tidak ditemukan.")
        session.clear()
        flash("Sesi Anda tidak valid, silakan login kembali.", "danger")
        return redirect(url_for("auth.login"))
    
    except OutOfStockError as oose:
        logger.warning(
            f"Checkout gagal untuk {user_log_id}: Stok habis: {oose}"
        )
        flash(str(oose), "danger")
        return redirect(url_for("purchase.cart_page"))
    
    except (DatabaseException, ServiceLogicError) as e:
        logger.error(
            f"Kesalahan memuat halaman checkout (GET) untuk {user_log_id}: {e}",
            exc_info=True,
        )
        flash(
            "Gagal memuat halaman checkout karena kesalahan server.", "danger"
        )
        return redirect(url_for("purchase.cart_page"))
    
    except Exception as e:
        logger.error(
            f"Kesalahan tak terduga saat memuat halaman checkout (GET) untuk {user_log_id}: {e}",
            exc_info=True,
        )
        flash("Gagal memuat halaman checkout.", "danger")
        return redirect(url_for("purchase.cart_page"))


@purchase_bp.route("/checkout/edit_address", methods=["GET", "POST"])
@login_required
def edit_address() -> Union[str, WerkzeugResponse]:
    user_id: int = session["user_id"]
    logger.debug(f"Pengguna {user_id} mengakses halaman edit alamat.")

    if request.method == "POST":
        address_data: Dict[str, Any] = {
            "phone": request.form.get("phone"),
            "address1": request.form.get("address_line_1"),
            "address2": request.form.get("address_line_2", ""),
            "city": request.form.get("city"),
            "province": request.form.get("province"),
            "postal_code": request.form.get("postal_code"),
        }
        logger.info(
            f"Pengguna {user_id} mengirim pembaruan alamat: {address_data}"
        )

        try:
            result: Dict[str, Any] = user_service.update_user_address(
                user_id, address_data
            )
            
            if result["success"]:
                flash("Alamat berhasil diperbarui.", "success")
                logger.info(
                    f"Alamat berhasil diperbarui untuk pengguna {user_id}."
                )
                return redirect(url_for("purchase.checkout"))
            
            else:
                flash(
                    result.get("message", "Gagal memperbarui alamat."),
                    "danger",
                )
                logger.warning(
                    f"Gagal memperbarui alamat untuk pengguna {user_id}: {result.get('message')}"
                )

        except (DatabaseException, ServiceLogicError) as e:
            logger.error(
                f"Kesalahan saat memperbarui alamat untuk pengguna {user_id} melalui rute checkout: {e}",
                exc_info=True,
            )
            flash(
                "Terjadi kesalahan server saat memperbarui alamat.", "danger"
            )

        except Exception as e:
            logger.error(
                f"Kesalahan tak terduga saat memperbarui alamat untuk pengguna {user_id} melalui rute checkout: {e}",
                exc_info=True,
            )
            flash(
                "Terjadi kesalahan server saat memperbarui alamat.", "danger"
            )
        return redirect(url_for("purchase.edit_address"))

    try:
        user: Dict[str, Any] = user_service.get_user_by_id(user_id)
        return render_template(
            "purchase/edit_address_page.html",
            user=user,
            content=get_content(),
        )
    
    except RecordNotFoundError:
        logger.error(
            f"Pengguna {user_id} tidak ditemukan saat mengakses halaman edit alamat."
        )
        flash("Pengguna tidak ditemukan.", "danger")
        return redirect(url_for("user.user_profile"))
    
    except (DatabaseException, ServiceLogicError) as e:
        logger.error(
            f"Kesalahan memuat halaman edit alamat untuk pengguna {user_id}: {e}",
            exc_info=True,
        )
        flash("Gagal memuat halaman edit alamat.", "danger")
        return redirect(url_for("purchase.checkout"))
    
    except Exception as e:
        logger.error(
            f"Kesalahan tak terduga memuat halaman edit alamat untuk pengguna {user_id}: {e}",
            exc_info=True,
        )
        flash("Gagal memuat halaman edit alamat.", "danger")
        return redirect(url_for("purchase.checkout"))