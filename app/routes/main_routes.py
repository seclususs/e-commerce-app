from flask import Blueprint, render_template, request, session, redirect, url_for, flash
import json
from database.db_config import get_db_connection, get_content
from utils.route_decorators import login_required

product_bp = Blueprint('product', __name__)

@product_bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('product.products_page'))
    conn = get_db_connection()
    top_products = conn.execute('SELECT * FROM products ORDER BY popularity DESC LIMIT 4').fetchall()
    conn.close()
    return render_template('public/landing_page.html', products=top_products, content=get_content(), is_homepage=True)

@product_bp.route('/home')
@login_required
def home():
    return redirect(url_for('product.products_page'))

@product_bp.route('/about')
def about():
    return render_template('public/about.html', content=get_content())

@product_bp.route('/products')
def products_page():
    conn = get_db_connection()
    search_term = request.args.get('search')
    category_id = request.args.get('category')
    sort_by = request.args.get('sort', 'popularity')
    
    query = "SELECT p.*, c.name as category_name FROM products p LEFT JOIN categories c ON p.category_id = c.id WHERE 1=1"
    params = []
    
    if search_term:
        query += " AND p.name LIKE ?"
        params.append(f'%{search_term}%')
    if category_id:
        query += " AND p.category_id = ?"
        params.append(category_id)
    
    if sort_by == 'price_asc':
        # Logika sorting harga dengan mempertimbangkan harga diskon
        query += " ORDER BY CASE WHEN p.discount_price IS NOT NULL AND p.discount_price > 0 THEN p.discount_price ELSE p.price END ASC"
    elif sort_by == 'price_desc':
        query += " ORDER BY CASE WHEN p.discount_price IS NOT NULL AND p.discount_price > 0 THEN p.discount_price ELSE p.price END DESC"
    else:
        query += " ORDER BY p.popularity DESC"
        
    products = conn.execute(query, params).fetchall()
    categories = conn.execute("SELECT * FROM categories ORDER BY name ASC").fetchall()
    conn.close()
    
    return render_template('public/product_catalog.html', products=products, categories=categories, content=get_content())

@product_bp.route('/product/<int:id>')
def product_detail(id):
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
    
    can_review = False
    if 'user_id' in session:
        user_id = session['user_id']
        conn.execute('UPDATE products SET popularity = popularity + 1 WHERE id = ?', (id,))
        conn.commit()
        
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
    rating = request.form.get('rating')
    comment = request.form.get('comment')
    user_id = session['user_id']

    if not rating or not comment:
        flash('Rating dan komentar tidak boleh kosong.', 'danger')
        return redirect(url_for('product.product_detail', id=id))

    conn = get_db_connection()

    has_purchased = conn.execute("""
        SELECT 1 FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        WHERE o.user_id = ? AND oi.product_id = ? AND o.status = 'Completed'
        LIMIT 1
    """, (user_id, id)).fetchone()

    if not has_purchased:
        flash('Anda harus membeli produk ini untuk memberikan ulasan.', 'danger')
        conn.close()
        return redirect(url_for('product.product_detail', id=id))

    has_reviewed = conn.execute(
        'SELECT 1 FROM reviews WHERE user_id = ? AND product_id = ? LIMIT 1',
        (user_id, id)
    ).fetchone()

    if has_reviewed:
        flash('Anda sudah pernah memberikan ulasan untuk produk ini.', 'danger')
        conn.close()
        return redirect(url_for('product.product_detail', id=id))

    conn.execute('INSERT INTO reviews (product_id, user_id, rating, comment) VALUES (?, ?, ?, ?)', (id, user_id, rating, comment))
    conn.commit()
    conn.close()
    
    flash('Terima kasih atas ulasan Anda!', 'success')
    return redirect(url_for('product.product_detail', id=id))