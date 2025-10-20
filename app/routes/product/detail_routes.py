from flask import render_template, request, session, redirect, url_for, flash
from db.db_config import get_content
from utils.route_decorators import login_required
from services.products.product_service import product_service
from services.products.review_service import review_service
from . import product_bp

@product_bp.route('/product/<int:id>')
def product_detail(id):
    """Menampilkan halaman detail untuk satu produk, termasuk ulasan dan validasi untuk ulasan baru."""
    product = product_service.get_product_by_id(id)
    
    if product is None:
        flash("Produk tidak ditemukan.", "danger")
        return redirect(url_for('product.products_page'))
        
    reviews = review_service.get_reviews_for_product(id)
    
    related_products = []
    if product.get('category_id'):
        related_products = product_service.get_related_products(id, product['category_id'])
    
    can_review = False
    if 'user_id' in session:
        can_review = review_service.check_user_can_review(session['user_id'], id)
        
    return render_template('public/product_detail.html', 
                           product=product, 
                           reviews=reviews, 
                           related_products=related_products,
                           content=get_content(), 
                           can_review=can_review)

@product_bp.route('/product/<int:id>/add_review', methods=['POST'])
@login_required
def add_review(id):
    """Menangani pengiriman form ulasan baru."""
    rating = request.form.get('rating')
    comment = request.form.get('comment')
    user_id = session['user_id']

    if not rating or not comment:
        flash('Rating dan komentar tidak boleh kosong.', 'danger')
        return redirect(url_for('product.product_detail', id=id))

    result = review_service.add_review(user_id, id, rating, comment)
    flash(result['message'], 'success' if result['success'] else 'danger')
    
    return redirect(url_for('product.product_detail', id=id))