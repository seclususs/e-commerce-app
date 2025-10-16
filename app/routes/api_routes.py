from flask import Blueprint, jsonify, request, session, url_for
from database.db_config import get_db_connection
from utils.route_decorators import login_required
from services.order_service import order_service
from services.user_service import user_service

api_bp = Blueprint('api', __name__)

@api_bp.route('/cart', methods=['POST'])
def get_cart_items():
    data = request.get_json()
    product_ids = data.get('product_ids')
    if not product_ids: return jsonify([])
    conn = get_db_connection()
    placeholders = ', '.join(['?'] * len(product_ids))
    # Ambil `discount_price` untuk dikirim ke frontend
    query = f'SELECT id, name, price, discount_price, image_url, stock FROM products WHERE id IN ({placeholders})'
    products = conn.execute(query, product_ids).fetchall()
    conn.close()
    return jsonify([dict(p) for p in products])

@api_bp.route('/quick_checkout', methods=['POST'])
@login_required
def quick_checkout():
    data = request.get_json()
    cart_data = data.get('cart')
    payment_method = data.get('payment_method')
    user_id = session['user_id']

    if not cart_data or not payment_method:
        return jsonify({'success': False, 'message': 'Data tidak lengkap.'}), 400

    user = user_service.get_user_by_id(user_id)
    if not user or not user.get('address_line_1'):
        return jsonify({
            'success': False, 
            'message': 'Alamat utama belum diatur. Silakan lengkapi alamat di halaman checkout.',
            'redirect': url_for('user.checkout')
        }), 400

    shipping_details = {
        'name': user['username'], 'phone': user['phone'],
        'address1': user['address_line_1'], 'address2': user.get('address_line_2', ''),
        'city': user['city'], 'province': user['province'],
        'postal_code': user['postal_code']
    }
    
    # Panggil service untuk membuat pesanan
    result = order_service.create_order(user_id, cart_data, shipping_details, payment_method, save_address=False)

    if result['success']:
        return jsonify({'success': True, 'order_id': result['order_id']})
    else:
        return jsonify({'success': False, 'message': result['message']}), 400