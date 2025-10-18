from flask import jsonify, request
from database.db_config import get_db_connection
from . import api_bp

@api_bp.route('/cart', methods=['POST'])
def get_cart_items():
    """
    Mengambil detail produk berdasarkan ID yang ada di keranjang belanja.
    """
    data = request.get_json()
    product_ids = data.get('product_ids')
    
    if not product_ids:
        return jsonify([])
        
    conn = get_db_connection()
    try:
        placeholders = ', '.join(['?'] * len(product_ids))
        # Ambil `discount_price` untuk dikirim ke frontend
        query = f'SELECT id, name, price, discount_price, image_url, stock FROM products WHERE id IN ({placeholders})'
        products = conn.execute(query, product_ids).fetchall()
        return jsonify([dict(p) for p in products])
    finally:
        conn.close()