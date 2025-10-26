from typing import Any, Dict, List, Optional, Tuple, Union

import mysql.connector
from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask.wrappers import Response
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursorDict
from werkzeug.wrappers import Response as WerkzeugResponse

from app.core.db import get_content, get_db_connection
from app.exceptions.api_exceptions import PermissionDeniedError
from app.exceptions.database_exceptions import (
    DatabaseException,
    RecordNotFoundError,
)
from app.exceptions.service_exceptions import (
    InvalidOperationError,
    ServiceLogicError,
)
from app.services.orders.order_cancel_service import order_cancel_service
from app.utils.logging_utils import get_logger
from app.utils.route_decorators import login_required

from . import purchase_bp

logger = get_logger(__name__)


@purchase_bp.route("/order/pay/<int:order_id>")
def payment_page(order_id: int) -> Union[str, WerkzeugResponse]:
    user_id: Optional[int] = session.get("user_id")
    guest_order_id: Optional[int] = session.get("guest_order_id")
    log_identifier: str = (
        f"ID Pengguna {user_id}"
        if user_id
        else f"ID Pesanan Tamu {guest_order_id}"
    )
    logger.debug(
        f"Mengakses halaman pembayaran untuk ID Pesanan: {order_id}. "
        f"Identitas: {log_identifier}"
    )

    conn: Optional[MySQLConnection] = None
    cursor: Optional[MySQLCursorDict] = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        order: Optional[Dict[str, Any]] = None

        if user_id:
            cursor.execute(
                "SELECT * FROM orders WHERE id = %s AND user_id = %s",
                (order_id, user_id),
            )
            order = cursor.fetchone()
        elif guest_order_id and guest_order_id == order_id:
            cursor.execute(
                "SELECT * FROM orders WHERE id = %s AND user_id IS NULL",
                (order_id,),
            )
            order = cursor.fetchone()

        if not order:
            logger.warning(
                f"Pesanan {order_id} tidak ditemukan atau akses ditolak untuk {log_identifier}."
            )
            raise PermissionDeniedError(
                "Pesanan tidak ditemukan atau tidak memerlukan pembayaran online."
            )

        if order["payment_method"] == "COD":
            logger.warning(
                f"Upaya mengakses halaman pembayaran untuk pesanan COD {order_id} oleh {log_identifier}."
            )
            flash(
                "Pesanan COD tidak memerlukan halaman pembayaran ini.", "info"
            )
            return redirect(url_for("purchase.order_success"))

        if order["status"] != "Menunggu Pembayaran":
            logger.info(
                f"Halaman pembayaran diakses untuk pesanan {order_id}, tetapi statusnya adalah '{order['status']}', mengarahkan ulang."
            )
            flash(
                f"Status pesanan ini adalah '{order['status']}'. Tidak perlu pembayaran.",
                "info",
            )
            if user_id:
                return redirect(url_for("user.user_profile"))
            return redirect(url_for("product.index"))

        cursor.execute(
            """
            SELECT p.name, oi.quantity, oi.price
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = %s
            """,
            (order_id,),
        )
        items: List[Dict[str, Any]] = cursor.fetchall()
        logger.info(
            f"Halaman pembayaran dimuat untuk ID Pesanan: {order_id}. Jumlah item: {len(items)}"
        )
        api_key: str = current_app.config["SECRET_KEY"]
        return render_template(
            "purchase/payment_page.html",
            order=order,
            items=items,
            content=get_content(),
            api_key=api_key,
        )
    
    except PermissionDeniedError as pde:
        flash(str(pde), "danger")
        return redirect(url_for("product.index"))
    
    except mysql.connector.Error as db_err:
        logger.error(
            f"Kesalahan database saat memuat halaman pembayaran untuk pesanan {order_id}: {db_err}",
            exc_info=True,
        )
        flash(
            "Gagal memuat halaman pembayaran karena kesalahan database.",
            "danger",
        )
        return redirect(url_for("product.index"))
    
    except Exception as e:
        logger.error(
            f"Terjadi kesalahan tak terduga saat memuat halaman pembayaran untuk pesanan {order_id}: {e}",
            exc_info=True,
        )
        flash("Gagal memuat halaman pembayaran.", "danger")
        return redirect(url_for("product.index"))
    
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@purchase_bp.route("/order_success")
def order_success() -> str:
    guest_order_details: Optional[Any] = session.pop(
        "guest_order_details", None
    )
    guest_order_id: Optional[int] = session.pop("guest_order_id", None)
    log_identifier: str = (
        f"ID Pengguna {session.get('user_id')}"
        if session.get("user_id")
        else f"ID Pesanan Tamu {guest_order_id}"
    )
    logger.info(
        f"Halaman keberhasilan pesanan diakses. Identitas: {log_identifier}. "
        f"Data pesanan tamu dihapus dari sesi: {'Ya' if guest_order_details else 'Tidak'}"
    )
    return render_template(
        "purchase/success_page.html",
        content=get_content(),
        guest_order_details=guest_order_details,
        guest_order_id=guest_order_id,
    )


@purchase_bp.route("/order/cancel/<int:order_id>", methods=["POST"])
@login_required
def cancel_order(
    order_id: int,
) -> Union[WerkzeugResponse, Tuple[Response, int]]:
    user_id: int = session["user_id"]
    logger.info(
        f"Pengguna {user_id} mencoba membatalkan pesanan dengan ID: {order_id}"
    )
    is_ajax: bool = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    
    try:
        result: Dict[str, Any] = order_cancel_service.cancel_user_order(
            order_id, user_id
        )

        if is_ajax:

            if result["success"]:
                logger.info(
                    f"Pesanan {order_id} berhasil dibatalkan melalui AJAX oleh pengguna {user_id}."
                )

            else:
                logger.warning(
                    f"Gagal membatalkan pesanan {order_id} melalui AJAX oleh pengguna {user_id}. Alasan: {result['message']}"
                )
            status_code: int = (
                200
                if result["success"]
                else (404 if "ditemukan" in result["message"] else 400)
            )

            return jsonify(result), status_code
        
        flash(
            result["message"], "success" if result["success"] else "danger"
        )

        if result["success"]:
            logger.info(
                f"Pesanan {order_id} berhasil dibatalkan oleh pengguna {user_id}."
            )

        else:
            logger.warning(
                f"Gagal membatalkan pesanan {order_id} oleh pengguna {user_id}. Alasan: {result['message']}"
            )

        return redirect(url_for("user.user_profile"))

    except (RecordNotFoundError, InvalidOperationError) as user_error:
        logger.warning(
            f"Pembatalan pesanan {order_id} oleh pengguna {user_id} gagal: {user_error}"
        )
        if is_ajax:
            status_code = (
                404
                if isinstance(user_error, RecordNotFoundError)
                else 400
            )
            return (
                jsonify(
                    {"success": False, "message": str(user_error)}
                ),
                status_code,
            )
        flash(str(user_error), "danger")
        return redirect(url_for("user.user_profile"))
    
    except (DatabaseException, ServiceLogicError) as service_err:
        logger.error(
            f"Kesalahan service/DB saat membatalkan pesanan {order_id} untuk pengguna {user_id}: {service_err}",
            exc_info=True,
        )
        if is_ajax:
            return (
                jsonify(
                    {"success": False, "message": "Terjadi kesalahan server."}
                ),
                500,
            )
        flash("Terjadi kesalahan saat membatalkan pesanan.", "danger")
        return redirect(url_for("user.user_profile"))
    
    except Exception as e:
        logger.error(
            f"Terjadi kesalahan tak terduga saat membatalkan pesanan {order_id} untuk pengguna {user_id}: {e}",
            exc_info=True,
        )
        if is_ajax:
            return (
                jsonify(
                    {"success": False, "message": "Terjadi kesalahan server."}
                ),
                500,
            )
        flash("Terjadi kesalahan saat membatalkan pesanan.", "danger")
        return redirect(url_for("user.user_profile"))