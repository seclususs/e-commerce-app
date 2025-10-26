from typing import Any, Dict, List, Optional

import mysql.connector
from flask import abort, flash, render_template, session
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursorDict

from app.core.db import get_content, get_db_connection
from app.exceptions.database_exceptions import (
    DatabaseException,
    RecordNotFoundError,
)
from app.exceptions.service_exceptions import ServiceLogicError
from app.utils.logging_utils import get_logger
from app.utils.route_decorators import login_required

from . import user_bp

logger = get_logger(__name__)


@user_bp.route("/order/track/<int:order_id>")
@login_required
def track_order(order_id: int) -> str:
    user_id: int = session["user_id"]
    logger.debug(
        f"Pengguna {user_id} meminta pelacakan untuk ID pesanan: {order_id}"
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
            """
            SELECT oi.*, p.name
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = %s
            """,
            (order_id,),
        )

        items: List[Dict[str, Any]] = cursor.fetchall()

        cursor.execute(
            """
            SELECT *
            FROM order_status_history
            WHERE order_id = %s
            ORDER BY timestamp DESC
            """,
            (order_id,),
        )

        history_list: List[Dict[str, Any]] = cursor.fetchall()
        logger.info(
            f"Data pelacakan berhasil diambil. {len(items)} item, "
            f"{len(history_list)} riwayat status ditemukan."
        )
        
        return render_template(
            "user/order_tracking.html",
            order=order,
            items=items,
            history_list=history_list,
            content=get_content(),
        )
    
    except RecordNotFoundError as rnfe:
        logger.warning(
            f"Kesalahan mengakses halaman lacak pesanan {order_id}: {rnfe}",
            exc_info=True,
        )
        abort(404, description=str(rnfe))

    except mysql.connector.Error as db_err:
        logger.error(
            f"Kesalahan database saat mengambil data pelacakan "
            f"untuk pesanan {order_id}: {db_err}",
            exc_info=True,
        )
        flash(
            "Gagal memuat informasi pelacakan karena kesalahan database.",
            "danger",
        )
        raise DatabaseException(
            f"Kesalahan database melacak pesanan {order_id}: {db_err}"
        )
    
    except Exception as e:
        logger.error(
            f"Kesalahan tak terduga saat mengambil data pelacakan "
            f"untuk pesanan {order_id}: {e}",
            exc_info=True,
        )
        flash("Gagal memuat informasi pelacakan.", "danger")
        raise ServiceLogicError(
            f"Kesalahan tak terduga melacak pesanan {order_id}: {e}"
        )
    
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()