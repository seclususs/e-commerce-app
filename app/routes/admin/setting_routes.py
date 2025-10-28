from typing import Any, Dict, Optional, Tuple, Union

from flask import Response, flash, jsonify, render_template, request
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursor

from app.core.db import get_content, get_db_connection
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.utils.logging_utils import get_logger
from app.utils.route_decorators import admin_required

from . import admin_bp

logger = get_logger(__name__)


@admin_bp.route("/settings", methods=["GET", "POST"])
@admin_required
def admin_settings() -> Union[str, Response, Tuple[Response, int]]:
    conn: Optional[MySQLConnection] = None
    cursor: Optional[MySQLCursor] = None
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method == "POST":
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            updated_count: int = 0

            for key, value in request.form.items():
                cursor.execute(
                    "UPDATE content SET value = %s WHERE `key` = %s", (value, key)
                )
                updated_count += cursor.rowcount

            conn.commit()
            return jsonify(
                {
                    "success": True,
                    "message": "Pengaturan situs berhasil diperbarui!",
                }
            )

        except DatabaseException:
            if conn and conn.is_connected():
                conn.rollback()
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Gagal memperbarui pengaturan karena kesalahan database.",
                    }
                ),
                500,
            )
        
        except Exception:
            if conn and conn.is_connected():
                conn.rollback()
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Gagal memperbarui pengaturan karena kesalahan server.",
                    }
                ),
                500,
            )
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    page_title = "Pengaturan Website - Admin"
    header_title = "Pengaturan Konten Website"

    try:
        content_data: Dict[str, Any] = get_content()

        if is_ajax:
            html = render_template(
                "partials/admin/_site_settings.html", content=content_data
            )
            return jsonify(
                {
                    "success": True,
                    "html": html,
                    "page_title": page_title,
                    "header_title": header_title,
                }
            )
        else:
            return render_template(
                "admin/site_settings.html", content=content_data
            )

    except (DatabaseException, ServiceLogicError):
        message = "Gagal memuat pengaturan situs."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        flash(message, "danger")
        return render_template("admin/site_settings.html", content={})
    
    except Exception:
        message = "Gagal memuat pengaturan situs."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        flash(message, "danger")
        return render_template("admin/site_settings.html", content={})