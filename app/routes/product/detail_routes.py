import json
from flask import render_template, request, session, redirect, url_for, flash
from database.db_config import get_db_connection, get_content
from utils.route_decorators import login_required
from . import product_bp

@product_bp.route('/product/<int:id>')
def product_detail(id):
    """Menampilkan halaman detail untuk satu produk, termasuk ulasan dan validasi untuk ulasan baru."""
    conn = get_db_connection()
    product_row = conn.execute('SELECT p.*, c.name as category_name FROM products p LEFT JOIN categories c ON p.category_id = c.id WHERE p.id = ?', (id,)).fetchone()
    
    if product_row is None:
        flash("Produk tidak ditemukan.", "danger")
        return redirect(url_for('product.products_page'))
        
    product = dict(product_row)
    reviews = conn.execute("""
        SELECT r.*, u.username FROM reviews r 
        JOIN users u ON r.user_id = u.id 
        WHERE r.product_id = ? ORDER BY r.created_at DESC
    """, (id,)).fetchall()
    
    try:
        product['additional_image_urls'] = json.loads(product['additional_image_urls']) if product['additional_image_urls'] else []
    except (json.JSONDecodeError, TypeError):
        product['additional_image_urls'] = []
    
    product['all_images'] = [product['image_url']] + product['additional_image_urls']
    
    # Meningkatkan popularitas produk setiap kali halaman diakses
    conn.execute('UPDATE products SET popularity = popularity + 1 WHERE id = ?', (id,))
    conn.commit()
    
    can_review = False
    if 'user_id' in session:
        user_id = session['user_id']
        
        has_purchased = conn.execute("""
            SELECT 1 FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            WHERE o.user_id = ? AND oi.product_id = ? AND o.status = 'Completed'
            LIMIT 1
        """, (user_id, id)).fetchone()

        if has_purchased:
            has_reviewed = conn.execute(
                'SELECT 1 FROM reviews WHERE user_id = ? AND product_id = ? LIMIT 1',
                (user_id, id)
            ).fetchone()
            if not has_reviewed:
                can_review = True
        
    conn.close()
    return render_template('public/product_detail.html', product=product, reviews=reviews, content=get_content(), can_review=can_review)

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

    conn = get_db_connection()
    try:
        has_purchased = conn.execute("""
            SELECT 1 FROM orders o JOIN order_items oi ON o.id = oi.order_id
            WHERE o.user_id = ? AND oi.product_id = ? AND o.status = 'Completed' LIMIT 1
        """, (user_id, id)).fetchone()

        if not has_purchased:
            flash('Anda harus membeli produk ini untuk memberikan ulasan.', 'danger')
            return redirect(url_for('product.product_detail', id=id))

        has_reviewed = conn.execute('SELECT 1 FROM reviews WHERE user_id = ? AND product_id = ? LIMIT 1', (user_id, id)).fetchone()
        if has_reviewed:
            flash('Anda sudah pernah memberikan ulasan untuk produk ini.', 'danger')
            return redirect(url_for('product.product_detail', id=id))

        conn.execute('INSERT INTO reviews (product_id, user_id, rating, comment) VALUES (?, ?, ?, ?)', (id, user_id, rating, comment))
        conn.commit()
        flash('Terima kasih atas ulasan Anda!', 'success')
    finally:
        conn.close()
    
    return redirect(url_for('product.product_detail', id=id))