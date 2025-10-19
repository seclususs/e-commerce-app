from flask import render_template, request, session, redirect, url_for, flash
from database.db_config import get_content
from utils.route_decorators import login_required
from services.product_service import product_service
from . import product_bp

@product_bp.route('/product/<int:id>')
def product_detail(id):
    """Menampilkan halaman detail untuk satu produk, termasuk ulasan dan validasi untuk ulasan baru."""
    product = product_service.get_product_by_id(id)
    
    if product is None:
        flash("Produk tidak ditemukan.", "danger")
        return redirect(url_for('product.products_page'))
        
    reviews = product_service.get_reviews_for_product(id)
    
    can_review = False
    if 'user_id' in session:
        can_review = product_service.check_user_can_review(session['user_id'], id)
        
    return render_template('public/product_detail.html', 
                           product=product, 
                           reviews=reviews, 
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

    result = product_service.add_review(user_id, id, rating, comment)
    flash(result['message'], 'success' if result['success'] else 'danger')
    
    return redirect(url_for('product.product_detail', id=id))