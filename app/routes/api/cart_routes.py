from flask import jsonify, request, session
from . import api_bp
from services.cart_service import cart_service
from utils.route_decorators import login_required

@api_bp.route('/cart', methods=['POST'])
def get_guest_cart_items():
    """
    Mengambil detail produk berdasarkan ID yang ada di keranjang belanja (untuk tamu).
    """
    data = request.get_json()
    product_ids = data.get('product_ids')
    
    if not product_ids:
        return jsonify([])
        
    from database.db_config import get_db_connection
    conn = get_db_connection()
    try:
        placeholders = ', '.join(['?'] * len(product_ids))
        query = f'SELECT id, name, price, discount_price, image_url, stock FROM products WHERE id IN ({placeholders})'
        products = conn.execute(query, product_ids).fetchall()
        return jsonify([dict(p) for p in products])
    finally:
        conn.close()

# Rute API untuk pengguna yang sudah login
@api_bp.route('/user-cart', methods=['GET'])
@login_required
def get_user_cart():
    """Mengambil seluruh isi keranjang pengguna dari database."""
    user_id = session['user_id']
    cart_data = cart_service.get_cart_details(user_id)
    return jsonify(cart_data)

@api_bp.route('/user-cart', methods=['POST'])
@login_required
def add_to_user_cart():
    """Menambahkan item ke keranjang pengguna."""
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    user_id = session['user_id']
    
    if not product_id or not isinstance(quantity, int) or quantity <= 0:
        return jsonify({'success': False, 'message': 'Data tidak valid.'}), 400

    result = cart_service.add_to_cart(user_id, product_id, quantity)
    return jsonify(result), 200 if result['success'] else 400

@api_bp.route('/user-cart/<int:product_id>', methods=['PUT'])
@login_required
def update_user_cart_item(product_id):
    """Mengupdate kuantitas item di keranjang."""
    data = request.get_json()
    quantity = data.get('quantity')
    user_id = session['user_id']

    if quantity is None or not isinstance(quantity, int):
        return jsonify({'success': False, 'message': 'Kuantitas tidak valid.'}), 400

    result = cart_service.update_cart_item(user_id, product_id, quantity)
    return jsonify(result)

@api_bp.route('/user-cart/merge', methods=['POST'])
@login_required
def merge_cart():
    """Menggabungkan keranjang lokal dari guest ke database setelah login."""
    local_cart = request.get_json().get('local_cart')
    if not local_cart:
        return jsonify({'success': True, 'message': 'Tidak ada keranjang lokal untuk digabung.'})
    
    user_id = session['user_id']
    result = cart_service.merge_local_cart_to_db(user_id, local_cart)
    return jsonify(result)