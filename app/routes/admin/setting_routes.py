from flask import render_template, request, redirect, url_for, flash

from . import admin_bp
from db.db_config import get_db_connection, get_content
from utils.route_decorators import admin_required

@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    conn = get_db_connection()
    if request.method == 'POST':
        for key, value in request.form.items():
            conn.execute('UPDATE content SET value = ? WHERE key = ?', (value, key))
        conn.commit()
        flash('Pengaturan konten berhasil diperbarui!', 'success')
        conn.close()
        return redirect(url_for('admin.admin_settings'))
    
    content_data = get_content() # get_content already closes the connection
    return render_template('admin/site_settings.html', content=content_data)