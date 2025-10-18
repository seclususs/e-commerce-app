from flask import render_template, request
from database.db_config import get_db_connection, get_content
from . import product_bp

@product_bp.route('/products')
def products_page():
    """Menampilkan halaman katalog produk dengan fungsionalitas filter, sorting, dan pencarian."""
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
    else: # Default sorting
        query += " ORDER BY p.popularity DESC"
        
    products = conn.execute(query, params).fetchall()
    categories = conn.execute("SELECT * FROM categories ORDER BY name ASC").fetchall()
    conn.close()
    
    return render_template('public/product_catalog.html', products=products, categories=categories, content=get_content())