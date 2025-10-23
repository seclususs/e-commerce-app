from flask import render_template, request, redirect, url_for, flash, jsonify
from . import admin_bp
from app.core.db import get_db_connection, get_content
from app.utils.route_decorators import admin_required


@admin_bp.route('/vouchers', methods=['GET', 'POST'])
@admin_required
def admin_vouchers():
    conn = get_db_connection()
    if request.method == 'POST':
        code = request.form.get('code', '').upper().strip()
        v_type = request.form.get('type')
        value = request.form.get('value')
        min_purchase = request.form.get('min_purchase_amount') or 0
        max_uses = request.form.get('max_uses') or None

        if not code or not v_type or not value:
            return jsonify({'success': False, 'message': 'Kode, Tipe, dan Nilai tidak boleh kosong.'}), 400

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO vouchers (code, type, value, min_purchase_amount, max_uses)
                VALUES (?, ?, ?, ?, ?)
                """,
                (code, v_type, value, min_purchase, max_uses)
            )
            new_id = cursor.lastrowid
            conn.commit()

            new_voucher = conn.execute("SELECT * FROM vouchers WHERE id = ?", (new_id,)).fetchone()
            html = render_template('admin/partials/_voucher_row.html', voucher=new_voucher)
            return jsonify({'success': True, 'message': f'Voucher "{code}" berhasil ditambahkan.', 'html': html})

        except conn.IntegrityError:
            return jsonify({'success': False, 'message': f'Kode voucher "{code}" sudah ada.'}), 400
        finally:
            if conn:
                conn.close()

    vouchers = conn.execute("SELECT * FROM vouchers ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('admin/manage_vouchers.html', vouchers=vouchers, content=get_content())


@admin_bp.route('/vouchers/delete/<int:id>', methods=['POST'])
@admin_required
def delete_voucher(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM vouchers WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Voucher berhasil dihapus.'})


@admin_bp.route('/vouchers/toggle/<int:id>', methods=['POST'])
@admin_required
def toggle_voucher(id):
    conn = get_db_connection()
    voucher = conn.execute("SELECT is_active FROM vouchers WHERE id = ?", (id,)).fetchone()
    if voucher:
        new_status = not voucher['is_active']
        conn.execute("UPDATE vouchers SET is_active = ? WHERE id = ?", (new_status, id))
        conn.commit()
        conn.close()
        message = f'Status voucher diubah menjadi {"Aktif" if new_status else "Tidak Aktif"}.'
        return jsonify({'success': True, 'message': message, 'data': {'is_active': new_status}})

    conn.close()
    return jsonify({'success': False, 'message': 'Voucher tidak ditemukan.'}), 404