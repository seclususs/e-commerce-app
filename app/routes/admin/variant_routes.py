from flask import render_template, request, redirect, url_for, flash
from . import admin_bp
from db.db_config import get_content
from utils.route_decorators import admin_required
from services.products.product_service import product_service
from services.products.variant_service import variant_service

@admin_bp.route('/product/<int:product_id>/variants', methods=['GET', 'POST'])
@admin_required
def manage_variants(product_id):
    """Menangani permintaan CRUD untuk varian produk."""
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            size = request.form.get('size')
            stock = request.form.get('stock')
            weight_grams = request.form.get('weight_grams')
            sku = request.form.get('sku')
            result = variant_service.add_variant(product_id, size, stock, weight_grams, sku)
            flash(result['message'], 'success' if result['success'] else 'danger')
        elif action == 'update':
            variant_id = request.form.get('variant_id')
            size = request.form.get('size')
            stock = request.form.get('stock')
            weight_grams = request.form.get('weight_grams')
            sku = request.form.get('sku')
            result = variant_service.update_variant(variant_id, size, stock, weight_grams, sku)
            flash(result['message'], 'success' if result['success'] else 'danger')
        
        # Perbarui total stok di tabel produk setelah ada perubahan
        variant_service.update_total_stock_from_variants(product_id)
        return redirect(url_for('admin.manage_variants', product_id=product_id))

    product = product_service.get_product_by_id(product_id)
    if not product or not product['has_variants']:
        flash('Produk tidak ditemukan atau tidak memiliki varian.', 'danger')
        return redirect(url_for('admin.admin_products'))
    
    variants = variant_service.get_variants_for_product(product_id)
    return render_template('admin/manage_variants.html', product=product, variants=variants, content=get_content())

@admin_bp.route('/product/<int:product_id>/variant/delete/<int:variant_id>')
@admin_required
def delete_variant(product_id, variant_id):
    """Menangani penghapusan varian."""
    result = variant_service.delete_variant(variant_id)
    flash(result['message'], 'success')
    # Perbarui total stok di tabel produk
    variant_service.update_total_stock_from_variants(product_id)
    return redirect(url_for('admin.manage_variants', product_id=product_id))