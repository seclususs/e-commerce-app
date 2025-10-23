from flask import render_template, request, redirect, url_for, flash, jsonify
from . import admin_bp
from app.core.db import get_content
from app.utils.route_decorators import admin_required
from app.services.products.product_service import product_service
from app.services.products.product_query_service import product_query_service
from app.services.products.product_bulk_service import product_bulk_service
from app.services.products.category_service import category_service


@admin_bp.route('/products', methods=['GET', 'POST'])
@admin_required
def admin_products():
    if request.method == 'POST':
        form_type = request.form.get('form_type')

        if form_type == 'bulk_action':
            action = request.form.get('bulk_action')
            selected_ids = request.form.getlist('product_ids')
            category_id = request.form.get('bulk_category_id')
            result = product_bulk_service.handle_bulk_product_action(action, selected_ids, category_id)

            if result['success']:
                result['ids'] = selected_ids
                result['action'] = action
                if action == 'set_category' and category_id:
                    category = category_service.get_category_by_id(category_id)
                    result['new_category_name'] = category['name'] if category else 'N/A'
                return jsonify(result)
            else:
                return jsonify(result), 400

        elif form_type == 'add_product':
            result = product_service.create_product(request.form, request.files)
            if result.get('success'):
                flash(result.get('message', 'Produk berhasil ditambahkan!'), 'success')
            else:
                flash(result.get('message', 'Gagal menambahkan produk.'), 'danger')
            return redirect(url_for('admin.admin_products'))

    search_term = request.args.get('search', '').strip()
    category_filter = request.args.get('category')
    stock_status_filter = request.args.get('stock_status')

    products = product_query_service.get_all_products_with_category(
        search=search_term,
        category_id=category_filter,
        stock_status=stock_status_filter
    )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'html': render_template('admin/partials/_product_table_body.html', products=products)
        })

    categories = category_service.get_all_categories()
    return render_template(
        'admin/manage_products.html',
        products=products,
        categories=categories,
        content=get_content(),
        search_term=search_term
    )


@admin_bp.route('/edit_product/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(id):
    if request.method == 'POST':
        result = product_service.update_product(id, request.form, request.files)
        if result['success']:
            result['redirect_url'] = url_for('admin.admin_products')
            return jsonify(result)
        return jsonify(result), 400

    product = product_query_service.get_product_by_id(id)
    if not product:
        flash('Produk tidak ditemukan.', 'danger')
        return redirect(url_for('admin.admin_products'))

    categories = category_service.get_all_categories()
    additional_images = product.get('additional_image_urls', [])

    return render_template(
        'admin/product_editor.html',
        product=product,
        additional_images=additional_images,
        categories=categories,
        content=get_content()
    )


@admin_bp.route('/delete_product/<int:id>', methods=['POST'])
@admin_required
def delete_product(id):
    result = product_service.delete_product(id)
    return jsonify(result)