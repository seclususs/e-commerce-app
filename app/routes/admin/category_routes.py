from flask import render_template, request, redirect, url_for, flash
from . import admin_bp
from db.db_config import get_content
from utils.route_decorators import admin_required
from services.products.category_service import category_service

@admin_bp.route('/categories', methods=['GET', 'POST'])
@admin_required
def admin_categories():
    """Menangani permintaan CRUD untuk kategori."""
    if request.method == 'POST':
        action = request.form.get('action')
        name = request.form.get('name')
        category_id = request.form.get('id')

        if action == 'add' and name:
            result = category_service.create_category(name)
            flash(result['message'], 'success' if result['success'] else 'danger')
        elif action == 'edit' and name and category_id:
            result = category_service.update_category(category_id, name)
            flash(result['message'], 'success')
        
        return redirect(url_for('admin.admin_categories'))
    
    categories = category_service.get_all_categories()
    return render_template('admin/manage_categories.html', categories=categories, content=get_content())

@admin_bp.route('/delete_category/<int:id>')
@admin_required
def delete_category(id):
    """Menangani penghapusan kategori."""
    result = category_service.delete_category(id)
    flash(result['message'], 'success')
    return redirect(url_for('admin.admin_categories'))