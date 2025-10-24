import mysql.connector
from flask import render_template, request, redirect, url_for, flash, jsonify
from app.core.db import get_db_connection, get_content
from app.utils.route_decorators import admin_required
from app.utils.logging_utils import get_logger
from . import admin_bp

logger = get_logger(__name__)


@admin_bp.route('/vouchers', methods=['GET', 'POST'])
@admin_required
def admin_vouchers():
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.method == 'POST':
            code = request.form.get('code', '').upper().strip()
            v_type = request.form.get('type')
            value = request.form.get('value')
            min_purchase = request.form.get('min_purchase_amount') or 0
            max_uses = request.form.get('max_uses') or None

            logger.debug(
                f"Mencoba menambahkan voucher. Kode: {code}, Tipe: {v_type}, "
                f"Nilai: {value}, Minimal Belanja: {min_purchase}, Maksimum Penggunaan: {max_uses}"
            )

            if not code or not v_type or not value:
                logger.warning("Gagal menambahkan voucher: Kolom wajib belum diisi.")
                return jsonify({
                    'success': False,
                    'message': 'Kode, Tipe, dan Nilai tidak boleh kosong.'
                }), 400

            try:
                cursor.execute(
                    """
                    INSERT INTO vouchers (code, type, value, min_purchase_amount, max_uses)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (code, v_type, value, min_purchase, max_uses)
                )
                new_id = cursor.lastrowid
                conn.commit()

                logger.info(f"Voucher '{code}' berhasil ditambahkan dengan ID: {new_id}")

                cursor.execute("SELECT * FROM vouchers WHERE id = %s", (new_id,))
                new_voucher = cursor.fetchone()

                html = render_template(
                    'admin/partials/_voucher_row.html',
                    voucher=new_voucher
                )
                return jsonify({
                    'success': True,
                    'message': f'Voucher \"{code}\" berhasil ditambahkan.',
                    'html': html
                })

            except mysql.connector.IntegrityError:
                conn.rollback()
                logger.warning(f"Gagal menambahkan voucher: kode '{code}' sudah ada.")
                return jsonify({
                    'success': False,
                    'message': f'Kode voucher \"{code}\" sudah terdaftar.'
                }), 400

            except Exception as e_inner:
                conn.rollback()
                logger.error(
                    f"Terjadi kesalahan saat menambahkan voucher '{code}': {e_inner}",
                    exc_info=True
                )
                return jsonify({
                    'success': False,
                    'message': 'Gagal menambahkan voucher karena kesalahan server.'
                }), 500

        logger.debug("Permintaan GET ke /vouchers. Mengambil data voucher...")

        cursor.execute("SELECT * FROM vouchers ORDER BY id DESC")
        vouchers = cursor.fetchall()

        logger.info(f"Berhasil mengambil {len(vouchers)} data voucher.")

        return render_template(
            'admin/manage_vouchers.html',
            vouchers=vouchers,
            content=get_content()
        )

    except Exception as e:
        logger.error(f"Kesalahan pada manajemen voucher: {e}", exc_info=True)
        flash("Gagal memuat halaman voucher.", "danger")

        return render_template(
            'admin/manage_vouchers.html',
            vouchers=[],
            content=get_content()
        )

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@admin_bp.route('/vouchers/delete/<int:id>', methods=['POST'])
@admin_required
def delete_voucher(id):
    conn = None
    cursor = None

    logger.debug(f"Mencoba menghapus voucher dengan ID: {id}")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM vouchers WHERE id = %s", (id,))
        conn.commit()

        if cursor.rowcount > 0:
            logger.info(f"Voucher ID {id} berhasil dihapus.")
            return jsonify({
                'success': True,
                'message': 'Voucher berhasil dihapus.'
            })

        logger.warning(f"Voucher ID {id} tidak ditemukan saat akan dihapus.")
        return jsonify({
            'success': False,
            'message': 'Voucher tidak ditemukan.'
        }), 404

    except Exception as e:
        if conn:
            conn.rollback()

        logger.error(
            f"Terjadi kesalahan saat menghapus voucher ID {id}: {e}",
            exc_info=True
        )
        return jsonify({
            'success': False,
            'message': 'Gagal menghapus voucher.'
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@admin_bp.route('/vouchers/toggle/<int:id>', methods=['POST'])
@admin_required
def toggle_voucher(id):
    conn = None
    cursor = None

    logger.debug(f"Mencoba mengubah status voucher dengan ID: {id}")

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT is_active FROM vouchers WHERE id = %s", (id,))
        voucher = cursor.fetchone()

        if voucher:
            new_status = not voucher['is_active']

            cursor.execute(
                "UPDATE vouchers SET is_active = %s WHERE id = %s",
                (new_status, id)
            )
            conn.commit()

            status_text = "Aktif" if new_status else "Tidak Aktif"
            logger.info(
                f"Status voucher ID {id} berhasil diubah menjadi {status_text}."
            )

            return jsonify({
                'success': True,
                'message': f'Status voucher berhasil diubah menjadi {status_text}.',
                'data': {'is_active': new_status}
            })

        logger.warning(f"Voucher ID {id} tidak ditemukan untuk diubah statusnya.")
        return jsonify({
            'success': False,
            'message': 'Voucher tidak ditemukan.'
        }), 404

    except Exception as e:
        if conn:
            conn.rollback()

        logger.error(
            f"Terjadi kesalahan saat mengubah status voucher ID {id}: {e}",
            exc_info=True
        )
        return jsonify({
            'success': False,
            'message': 'Gagal mengubah status voucher.'
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()