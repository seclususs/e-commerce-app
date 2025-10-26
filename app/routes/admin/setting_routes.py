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

    if request.method == "POST":
        logger.info("Memproses permintaan POST untuk memperbarui pengaturan situs.")

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            updated_count: int = 0

            for key, value in request.form.items():
                logger.debug(f"Memperbarui pengaturan: {key} = {value}")
                cursor.execute(
                    "UPDATE content SET value = %s WHERE `key` = %s", (value, key)
                )
                updated_count += cursor.rowcount

            conn.commit()
            logger.info(
                f"Pengaturan situs berhasil diperbarui. "
                f"{updated_count} baris terpengaruh."
            )

            return jsonify(
                {"success": True, "message": "Pengaturan situs berhasil diperbarui!"}
            )

        except DatabaseException as de:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan database saat memperbarui pengaturan: {de}",
                exc_info=True,
            )
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Gagal memperbarui pengaturan karena "
                        "kesalahan database.",
                    }
                ),
                500,
            )
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Terjadi kesalahan tak terduga saat memperbarui "
                f"pengaturan situs: {e}",
                exc_info=True,
            )
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Gagal memperbarui pengaturan karena "
                        "kesalahan server.",
                    }
                ),
                500,
            )

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    logger.debug("Mengambil data pengaturan situs untuk permintaan GET.")
    
    try:
        content_data: Dict[str, Any] = get_content()
        logger.info("Data pengaturan situs berhasil diambil.")
        return render_template("admin/site_settings.html", content=content_data)
    
    except (DatabaseException, ServiceLogicError) as service_err:
        logger.error(
            f"Kesalahan saat mengambil pengaturan situs: {service_err}",
            exc_info=True,
        )
        flash("Gagal memuat pengaturan situs.", "danger")
        return render_template("admin/site_settings.html", content={})
    
    except Exception as e:
        logger.error(
            f"Terjadi kesalahan tak terduga saat mengambil "
            f"data pengaturan situs: {e}",
            exc_info=True,
        )
        flash("Gagal memuat pengaturan situs.", "danger")
        return render_template("admin/site_settings.html", content={})