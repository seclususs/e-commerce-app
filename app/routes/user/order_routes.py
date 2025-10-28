from typing import Any, Dict, List, Optional, Union, Tuple

import mysql.connector
from flask import (
    Response, abort, flash, jsonify, redirect,
    render_template, request, session, url_for
)
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursorDict

from app.core.db import get_content, get_db_connection
from app.exceptions.database_exceptions import RecordNotFoundError
from app.utils.logging_utils import get_logger
from app.utils.route_decorators import login_required

from . import user_bp

logger = get_logger(__name__)


@user_bp.route("/order/track/<int:order_id>")
@login_required
def track_order(order_id: int) -> Union[str, Response, Tuple[Response, int]]:
    user_id: int = session["user_id"]
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    logger.debug(
        f"Pengguna {user_id} meminta pelacakan (AJAX: {is_ajax}) "
        f"untuk ID pesanan: {order_id}"
    )
    page_title = (
        f"Lacak Pesanan #{order_id} - "
        f"{get_content().get('app_name', 'App')}"
    )
    conn: Optional[MySQLConnection] = None
    cursor: Optional[MySQLCursorDict] = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM orders WHERE id = %s AND user_id = %s",
            (order_id, user_id),
        )

        order: Optional[Dict[str, Any]] = cursor.fetchone()

        if not order:
            logger.warning(
                f"Pesanan {order_id} tidak ditemukan atau akses ditolak "
                f"untuk pengguna {user_id}."
            )
            raise RecordNotFoundError(
                "Pesanan tidak ditemukan atau Anda tidak memiliki akses."
            )

        cursor.execute(
            "SELECT oi.*, p.name FROM order_items oi "
            "JOIN products p ON oi.product_id = p.id "
            "WHERE oi.order_id = %s",
            (order_id,),
        )

        items: List[Dict[str, Any]] = cursor.fetchall()

        cursor.execute(
            "SELECT * FROM order_status_history "
            "WHERE order_id = %s ORDER BY timestamp DESC",
            (order_id,),
        )

        history_list: List[Dict[str, Any]] = cursor.fetchall()
        logger.info(
            f"Data pelacakan diambil: {len(items)} item, "
            f"{len(history_list)} riwayat status."
        )

        render_args = {
            "order": order,
            "items": items,
            "history_list": history_list,
            "content": get_content(),
        }

        if is_ajax:
            html = render_template(
                "partials/user/_order_tracking.html", **render_args
            )
            return jsonify(
                {"success": True, "html": html, "page_title": page_title}
            )
        else:
            return render_template(
                "user/order_tracking.html", **render_args
            )

    except RecordNotFoundError as rnfe:
        logger.warning(
            f"Kesalahan akses halaman lacak pesanan {order_id}: {rnfe}",
            exc_info=True,
        )
        message = str(rnfe)
        if is_ajax:
            return jsonify({"success": False, "message": message}), 404
        abort(404, description=message)

    except mysql.connector.Error as db_err:
        logger.error(
            f"Kesalahan DB mengambil pelacakan pesanan {order_id}: {db_err}",
            exc_info=True,
        )
        message = "Gagal memuat informasi pelacakan karena kesalahan database."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        flash(message, "danger")
        return redirect(url_for("user.user_profile"))
    
    except Exception as e:
        logger.error(
            f"Kesalahan tak terduga mengambil pelacakan pesanan {order_id}: {e}",
            exc_info=True,
        )
        message = "Gagal memuat informasi pelacakan."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        flash(message, "danger")
        return redirect(url_for("user.user_profile"))
    
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()