from flask import render_template, request, redirect, url_for, flash
from . import admin_bp
from database.db_config import get_db_connection, get_content
from utils.route_decorators import admin_required

@admin_bp.route('/vouchers', methods=['GET', 'POST'])
@admin_required
def admin_vouchers():
    """Menangani manajemen voucher (CRUD)."""
    conn = get_db_connection()
    if request.method == 'POST':
        code = request.form['code'].upper().strip()
        v_type = request.form['type']
        value = request.form['value']
        min_purchase = request.form.get('min_purchase_amount') or 0
        max_uses = request.form.get('max_uses') or None
        
        if not code or not v_type or not value:
            flash('Kode, Tipe, dan Nilai tidak boleh kosong.', 'danger')
        else:
            try:
                conn.execute("""
                    INSERT INTO vouchers (code, type, value, min_purchase_amount, max_uses)
                    VALUES (?, ?, ?, ?, ?)
                """, (code, v_type, value, min_purchase, max_uses))
                conn.commit()
                flash(f'Voucher "{code}" berhasil ditambahkan.', 'success')
            except conn.IntegrityError:
                flash(f'Kode voucher "{code}" sudah ada.', 'danger')
        
        conn.close()
        return redirect(url_for('admin.admin_vouchers'))

    vouchers = conn.execute("SELECT * FROM vouchers ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('admin/manage_vouchers.html', vouchers=vouchers, content=get_content())

@admin_bp.route('/vouchers/delete/<int:id>')
@admin_required
def delete_voucher(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM vouchers WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash('Voucher berhasil dihapus.', 'success')
    return redirect(url_for('admin.admin_vouchers'))

@admin_bp.route('/vouchers/toggle/<int:id>')
@admin_required
def toggle_voucher(id):
    conn = get_db_connection()
    voucher = conn.execute("SELECT is_active FROM vouchers WHERE id = ?", (id,)).fetchone()
    if voucher:
        new_status = not voucher['is_active']
        conn.execute("UPDATE vouchers SET is_active = ? WHERE id = ?", (new_status, id))
        conn.commit()
        flash(f'Status voucher diubah menjadi {"Aktif" if new_status else "Tidak Aktif"}.', 'success')
    conn.close()
    return redirect(url_for('admin.admin_vouchers'))