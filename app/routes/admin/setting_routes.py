from flask import render_template, request, redirect, url_for, flash, jsonify

from . import admin_bp
from db.db_config import get_db_connection, get_content
from utils.route_decorators import admin_required

@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    if request.method == 'POST':
        conn = get_db_connection()
        try:
            with conn:
                for key, value in request.form.items():
                    conn.execute('UPDATE content SET value = ? WHERE key = ?', (value, key))
            return jsonify({'success': True, 'message': 'Pengaturan konten berhasil diperbarui!'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'Terjadi kesalahan: {e}'}), 500
        finally:
            if conn:
                conn.close()
    
    content_data = get_content() 
    return render_template('admin/site_settings.html', content=content_data)