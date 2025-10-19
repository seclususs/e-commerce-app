from flask import render_template, request, redirect, url_for, flash
from . import admin_bp
from database.db_config import get_content
from utils.route_decorators import admin_required
from services.product_service import product_service

@admin_bp.route('/products', methods=['GET', 'POST'])
@admin_required
def admin_products():
    if request.method == 'POST':
        if 'bulk_action' in request.form and request.form.get('bulk_action'):
            action = request.form.get('bulk_action')
            selected_ids = request.form.getlist('product_ids')
            category_id = request.form.get('bulk_category_id')
            result = product_service.handle_bulk_product_action(action, selected_ids, category_id)
            flash(result['message'], 'success' if result['success'] else 'danger')
        else:
            result = product_service.create_product(request.form, request.files)
            flash(result['message'], 'success' if result['success'] else 'danger')
        
        return redirect(url_for('admin.admin_products'))
    
    products = product_service.get_all_products_with_category()
    categories = product_service.get_all_categories()
    return render_template('admin/manage_products.html', products=products, categories=categories, content=get_content())

@admin_bp.route('/edit_product/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(id):
    if request.method == 'POST':
        result = product_service.update_product(id, request.form, request.files)
        flash(result['message'], 'success' if result['success'] else 'danger')
        if result['success']:
            return redirect(url_for('admin.admin_products'))
        return redirect(url_for('admin.admin_edit_product', id=id))

    product = product_service.get_product_by_id(id)
    if not product:
        flash('Produk tidak ditemukan.', 'danger')
        return redirect(url_for('admin.admin_products'))
    
    categories = product_service.get_all_categories()
    additional_images = product.get('additional_image_urls', [])
    
    return render_template('admin/product_editor.html', 
                           product=product, 
                           additional_images=additional_images, 
                           categories=categories, 
                           content=get_content())

@admin_bp.route('/delete_product/<int:id>')
@admin_required
def delete_product(id):
    result = product_service.delete_product(id)
    flash(result['message'], 'success' if result['success'] else 'danger')
    return redirect(url_for('admin.admin_products'))

# Rute untuk Varian
@admin_bp.route('/product/<int:product_id>/variants', methods=['GET', 'POST'])
@admin_required
def manage_variants(product_id):
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            size = request.form.get('size')
            stock = request.form.get('stock')
            result = product_service.add_variant(product_id, size, stock)
            flash(result['message'], 'success' if result['success'] else 'danger')
        elif action == 'update':
            variant_id = request.form.get('variant_id')
            size = request.form.get('size')
            stock = request.form.get('stock')
            result = product_service.update_variant(variant_id, size, stock)
            flash(result['message'], 'success' if result['success'] else 'danger')
        
        # Perbarui total stok di tabel produk setelah ada perubahan
        product_service.update_total_stock_from_variants(product_id)
        return redirect(url_for('admin.manage_variants', product_id=product_id))

    product = product_service.get_product_by_id(product_id)
    if not product:
        flash('Produk tidak ditemukan.', 'danger')
        return redirect(url_for('admin.admin_products'))
    
    variants = product_service.get_variants_for_product(product_id)
    return render_template('admin/manage_variants.html', product=product, variants=variants, content=get_content())

@admin_bp.route('/product/<int:product_id>/variant/delete/<int:variant_id>')
@admin_required
def delete_variant(product_id, variant_id):
    result = product_service.delete_variant(variant_id)
    flash(result['message'], 'success')
    # Perbarui total stok di tabel produk
    product_service.update_total_stock_from_variants(product_id)
    return redirect(url_for('admin.manage_variants', product_id=product_id))


# Rute untuk Kategori
@admin_bp.route('/categories', methods=['GET', 'POST'])
@admin_required
def admin_categories():
    if request.method == 'POST':
        action = request.form.get('action')
        name = request.form.get('name')
        category_id = request.form.get('id')

        if action == 'add' and name:
            result = product_service.create_category(name)
            flash(result['message'], 'success' if result['success'] else 'danger')
        elif action == 'edit' and name and category_id:
            result = product_service.update_category(category_id, name)
            flash(result['message'], 'success')
        
        return redirect(url_for('admin.admin_categories'))
    
    categories = product_service.get_all_categories()
    return render_template('admin/manage_categories.html', categories=categories, content=get_content())

@admin_bp.route('/delete_category/<int:id>')
@admin_required
def delete_category(id):
    result = product_service.delete_category(id)
    flash(result['message'], 'success')
    return redirect(url_for('admin.admin_categories'))