from flask import render_template, request, redirect, url_for, flash, jsonify
from app.core.db import get_db_connection, get_content, get_db
from app.utils.route_decorators import admin_required
from app.utils.logging_utils import get_logger
from . import admin_bp

logger = get_logger(__name__)


@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    conn = None
    cursor = None

    if request.method == 'POST':
        logger.info("Memproses permintaan POST untuk memperbarui pengaturan situs.")

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            updated_count = 0

            for key, value in request.form.items():
                logger.debug(f"Memperbarui pengaturan: {key} = {value}")
                cursor.execute(
                    'UPDATE content SET value = %s WHERE `key` = %s',
                    (value, key)
                )
                updated_count += cursor.rowcount

            conn.commit()
            logger.info(
                f"Pengaturan situs berhasil diperbarui. {updated_count} baris terpengaruh."
            )
            return jsonify({
                'success': True,
                'message': 'Pengaturan situs berhasil diperbarui!'
            })

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(
                f"Terjadi kesalahan saat memperbarui pengaturan situs: {e}",
                exc_info=True
            )
            return jsonify({
                'success': False,
                'message': f'Terjadi kesalahan: {e}'
            }), 500

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    logger.debug("Mengambil data pengaturan situs untuk permintaan GET.")

    try:
        content_data = get_content()
        logger.info("Data pengaturan situs berhasil diambil.")
        return render_template(
            'admin/site_settings.html',
            content=content_data
        )

    except Exception as e:
        logger.error(
            f"Terjadi kesalahan saat mengambil data pengaturan situs: {e}",
            exc_info=True
        )
        flash("Gagal memuat pengaturan situs.", "danger")
        return render_template(
            'admin/site_settings.html',
            content={}
        )