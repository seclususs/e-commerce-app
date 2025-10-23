from flask import render_template, request, redirect, url_for, flash, jsonify
from . import admin_bp
from app.core.db import get_content
from app.utils.route_decorators import admin_required
from app.services.products.category_service import category_service


@admin_bp.route('/categories', methods=['GET', 'POST'])
@admin_required
def admin_categories():
    if request.method == 'POST':
        action = request.form.get('action')
        name = request.form.get('name')
        category_id = request.form.get('id')

        result = {'success': False, 'message': 'Aksi tidak valid.'}
        status_code = 400

        if action == 'add' and name:
            result = category_service.create_category(name)
            if result.get('success'):
                html = render_template('admin/partials/_category_row.html', category=result['data'])
                result['html'] = html
                status_code = 200

        elif action == 'edit' and name and category_id:
            result = category_service.update_category(category_id, name)
            if result.get('success'):
                result['data'] = {'id': category_id, 'name': name}
                status_code = 200

        return jsonify(result), status_code

    categories = category_service.get_all_categories()
    return render_template('admin/manage_categories.html', categories=categories, content=get_content())


@admin_bp.route('/delete_category/<int:id>', methods=['POST'])
@admin_required
def delete_category(id):
    result = category_service.delete_category(id)
    return jsonify(result)