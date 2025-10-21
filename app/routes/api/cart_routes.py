import uuid
from flask import jsonify, request, session
from . import api_bp
from services.orders.cart_service import cart_service
from services.orders.stock_service import stock_service
from utils.route_decorators import login_required

@api_bp.route('/cart', methods=['POST'])
def get_guest_cart_items():
    """
    Mengambil detail produk berdasarkan item di keranjang belanja (untuk tamu).
    Logika dipindahkan ke cart_service.
    """
    data = request.get_json()
    cart_items = data.get('cart_items')

    if not cart_items:
        return jsonify([])
    
    detailed_items = cart_service.get_guest_cart_details(cart_items)
    return jsonify(detailed_items)


@api_bp.route('/user-cart', methods=['GET'])
@login_required
def get_user_cart():
    user_id = session['user_id']
    cart_data = cart_service.get_cart_details(user_id)
    return jsonify(cart_data)

@api_bp.route('/user-cart', methods=['POST'])
@login_required
def add_to_user_cart():
    data = request.get_json()
    product_id = data.get('product_id')
    variant_id = data.get('variant_id')
    quantity = data.get('quantity', 1)
    user_id = session['user_id']
    
    if not product_id or not isinstance(quantity, int) or quantity <= 0:
        return jsonify({'success': False, 'message': 'Data tidak valid.'}), 400

    result = cart_service.add_to_cart(user_id, product_id, quantity, variant_id)
    return jsonify(result), 200 if result['success'] else 400

@api_bp.route('/user-cart/<int:product_id>/<variant_id>', methods=['PUT'])
@login_required
def update_user_cart_item(product_id, variant_id):
    """Mengupdate kuantitas item di keranjang."""
    v_id = None if variant_id == 'null' else int(variant_id)

    data = request.get_json()
    quantity = data.get('quantity')
    user_id = session['user_id']

    if quantity is None or not isinstance(quantity, int):
        return jsonify({'success': False, 'message': 'Kuantitas tidak valid.'}), 400

    result = cart_service.update_cart_item(user_id, product_id, quantity, v_id)
    return jsonify(result)


@api_bp.route('/user-cart/merge', methods=['POST'])
@login_required
def merge_cart():
    local_cart = request.get_json().get('local_cart')
    if not local_cart:
        return jsonify({'success': True, 'message': 'Tidak ada keranjang lokal untuk digabung.'})
    
    user_id = session['user_id']
    result = cart_service.merge_local_cart_to_db(user_id, local_cart)
    return jsonify(result)

@api_bp.route('/checkout/prepare', methods=['POST'])
def prepare_guest_checkout():
    if 'user_id' in session:
        return jsonify({'success': False, 'message': 'Endpoint ini hanya untuk tamu.'}), 403

    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    session_id = session['session_id']

    items_to_hold = request.get_json().get('items')
    if not items_to_hold or not isinstance(items_to_hold, list):
        return jsonify({'success': False, 'message': 'Data keranjang tidak valid.'}), 400

    formatted_items = []
    for item in items_to_hold:
        formatted_items.append({
            'id': item['id'],
            'name': item['name'],
            'size': item.get('size'),
            'variant_id': item.get('variant_id'),
            'quantity': item['quantity']
        })

    hold_result = stock_service.hold_stock_for_checkout(None, session_id, formatted_items)
    return jsonify(hold_result)