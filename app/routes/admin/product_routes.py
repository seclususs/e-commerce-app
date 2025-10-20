from flask import render_template, request, redirect, url_for, flash
from . import admin_bp
from db.db_config import get_content
from utils.route_decorators import admin_required
from services.products.product_service import product_service
from services.products.category_service import category_service

@admin_bp.route('/products', methods=['GET', 'POST'])
@admin_required
def admin_products():
    """Menangani daftar produk dan pembuatan produk baru."""
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
    
    # Handle GET request with search
    search_term = request.args.get('search', '').strip()
    products = product_service.get_all_products_with_category(search=search_term)
    categories = category_service.get_all_categories()
    return render_template('admin/manage_products.html', 
                           products=products, 
                           categories=categories, 
                           content=get_content(),
                           search_term=search_term)

@admin_bp.route('/edit_product/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(id):
    """Menangani pembaruan produk."""
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
    
    categories = category_service.get_all_categories()
    additional_images = product.get('additional_image_urls', [])
    
    return render_template('admin/product_editor.html', 
                           product=product, 
                           additional_images=additional_images, 
                           categories=categories, 
                           content=get_content())

@admin_bp.route('/delete_product/<int:id>')
@admin_required
def delete_product(id):
    """Menangani penghapusan produk."""
    result = product_service.delete_product(id)
    flash(result['message'], 'success' if result['success'] else 'danger')
    return redirect(url_for('admin.admin_products'))