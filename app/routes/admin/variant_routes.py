from flask import render_template, request, redirect, url_for, flash, jsonify
from . import admin_bp
from app.core.db import get_content
from app.utils.route_decorators import admin_required
from app.services.products.product_query_service import product_query_service
from app.services.products.variant_service import variant_service


@admin_bp.route('/product/<int:product_id>/variants', methods=['GET', 'POST'])
@admin_required
def manage_variants(product_id):
    if request.method == 'POST':
        action = request.form.get('action')
        result = {'success': False, 'message': 'Aksi tidak valid'}
        status_code = 400

        if action == 'add':
            result = variant_service.add_variant(
                product_id, request.form.get('size'), request.form.get('stock'),
                request.form.get('weight_grams'), request.form.get('sku')
            )
            if result.get('success'):
                status_code = 200
                html = render_template('admin/partials/_variant_row.html', variant=result['data'], product_id=product_id)
                result['html'] = html
                variant_service.update_total_stock_from_variants(product_id)

        elif action == 'update':
            result = variant_service.update_variant(
                request.form.get('variant_id'), request.form.get('size'), request.form.get('stock'),
                request.form.get('weight_grams'), request.form.get('sku')
            )
            if result.get('success'):
                status_code = 200
                result['data'] = dict(request.form)
                variant_service.update_total_stock_from_variants(product_id)

        return jsonify(result), status_code

    product = product_query_service.get_product_by_id(product_id)
    if not product or not product['has_variants']:
        flash('Produk tidak ditemukan atau tidak memiliki varian.', 'danger')
        return redirect(url_for('admin.admin_products'))

    variants = variant_service.get_variants_for_product(product_id)
    return render_template(
        'admin/manage_variants.html',
        product=product,
        variants=variants,
        content=get_content(),
        product_id=product_id
    )


@admin_bp.route('/product/<int:product_id>/variant/delete/<int:variant_id>', methods=['POST'])
@admin_required
def delete_variant(product_id, variant_id):
    result = variant_service.delete_variant(variant_id)
    if result.get('success'):
        variant_service.update_total_stock_from_variants(product_id)
    return jsonify(result)