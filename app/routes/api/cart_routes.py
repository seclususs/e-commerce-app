import uuid
from flask import jsonify, request, session
from app.services.orders.cart_service import cart_service
from app.services.orders.stock_service import stock_service
from app.utils.route_decorators import login_required
from app.utils.logging_utils import get_logger
from . import api_bp

logger = get_logger(__name__)


@api_bp.route('/cart', methods=['POST'])
def get_guest_cart_items():
    data = request.get_json()
    cart_items = data.get('cart_items')
    logger.debug(f"Mengambil detail keranjang tamu untuk item: {cart_items}")

    if not cart_items:
        logger.info("Keranjang tamu kosong atau data tidak valid.")
        return jsonify([])

    try:
        detailed_items = cart_service.get_guest_cart_details(cart_items)
        logger.info(f"Detail keranjang tamu berhasil diambil. Jumlah item: {len(detailed_items)}")
        return jsonify(detailed_items)

    except Exception as e:
        logger.error(f"Terjadi kesalahan saat mengambil detail keranjang tamu: {e}", exc_info=True)
        return jsonify({
            "error": "Gagal mengambil detail keranjang."
            }), 500


@api_bp.route('/user-cart', methods=['GET'])
@login_required
def get_user_cart():
    user_id = session['user_id']
    logger.debug(f"Mengambil detail keranjang untuk user_id: {user_id}")

    try:
        cart_data = cart_service.get_cart_details(user_id)
        logger.info(
            f"Detail keranjang berhasil diambil untuk user_id: {user_id}. "
            f"Jumlah item: {len(cart_data.get('items', []))}"
        )
        return jsonify(cart_data)

    except Exception as e:
        logger.error(f"Terjadi kesalahan saat mengambil keranjang user {user_id}: {e}", exc_info=True)
        return jsonify({"error": "Gagal mengambil detail keranjang."}), 500


@api_bp.route('/user-cart', methods=['POST'])
@login_required
def add_to_user_cart():
    data = request.get_json()
    product_id = data.get('product_id')
    variant_id = data.get('variant_id')
    quantity = data.get('quantity', 1)
    user_id = session['user_id']

    logger.debug(
        f"Menambahkan item ke keranjang untuk user_id: {user_id}. "
        f"Produk: {product_id}, Varian: {variant_id}, Jumlah: {quantity}"
    )

    if not product_id or not isinstance(quantity, int) or quantity <= 0:
        logger.warning(
            f"Permintaan penambahan item tidak valid untuk user_id: {user_id}. Data: {data}"
        )
        return jsonify({
            'success': False, 
            'message': 'Data tidak valid.'
            }), 400

    try:
        result = cart_service.add_to_cart(user_id, product_id, quantity, variant_id)
        if result['success']:
            logger.info(
                f"Item berhasil ditambahkan untuk user_id: {user_id}. "
                f"Produk: {product_id}, Varian: {variant_id}"
            )
        else:
            logger.warning(
                f"Gagal menambahkan item untuk user_id: {user_id}. Alasan: {result['message']}"
            )
        return jsonify(result), 200 if result['success'] else 400

    except Exception as e:
        logger.error(
            f"Terjadi kesalahan saat menambahkan item ke keranjang user {user_id}: {e}",
            exc_info=True
        )
        return jsonify({
            'success': False, 
            'message': 'Gagal menambahkan item ke keranjang.'
            }), 500


@api_bp.route('/user-cart/<int:product_id>/<variant_id>', methods=['PUT'])
@login_required
def update_user_cart_item(product_id, variant_id):
    variant_value = None if variant_id == 'null' else int(variant_id)
    data = request.get_json()
    quantity = data.get('quantity')
    user_id = session['user_id']

    logger.debug(
        f"Memperbarui item keranjang untuk user_id: {user_id}. "
        f"Produk: {product_id}, Varian: {variant_value}, Jumlah baru: {quantity}"
    )

    if quantity is None or not isinstance(quantity, int):
        logger.warning(
            f"Permintaan pembaruan keranjang tidak valid untuk user_id: {user_id}. Data: {data}"
        )
        return jsonify({
            'success': False, 
            'message': 'Kuantitas tidak valid.'
            }), 400

    try:
        result = cart_service.update_cart_item(user_id, product_id, quantity, variant_value)
        if result['success']:
            logger.info(
                f"Item keranjang berhasil diperbarui untuk user_id: {user_id}. "
                f"Produk: {product_id}, Varian: {variant_value}, Kuantitas: {quantity}"
            )
        else:
            logger.warning(
                f"Gagal memperbarui item keranjang untuk user_id: {user_id}. "
                f"Alasan: {result.get('message', 'Tidak diketahui')}"
            )
        return jsonify(result)

    except Exception as e:
        logger.error(
            f"Terjadi kesalahan saat memperbarui item keranjang user {user_id}: {e}",
            exc_info=True
        )
        return jsonify({
            'success': False, 
            'message': 'Gagal memperbarui item keranjang.'
            }), 500


@api_bp.route('/user-cart/merge', methods=['POST'])
@login_required
def merge_cart():
    local_cart = request.get_json().get('local_cart')
    user_id = session['user_id']

    logger.debug(
        f"Mencoba menggabungkan keranjang lokal untuk user_id: {user_id}. "
        f"Kunci keranjang lokal: {list(local_cart.keys()) if local_cart else 'None'}"
    )

    if not local_cart:
        logger.info(f"Tidak ada keranjang lokal untuk digabung untuk user_id: {user_id}")
        return jsonify({
            'success': True, 
            'message': 'Tidak ada keranjang lokal untuk digabung.'
            })

    try:
        result = cart_service.merge_local_cart_to_db(user_id, local_cart)
        if result['success']:
            logger.info(f"Keranjang lokal berhasil digabung untuk user_id: {user_id}")
        else:
            logger.warning(
                f"Gagal menggabungkan keranjang lokal untuk user_id: {user_id}. "
                f"Alasan: {result['message']}"
            )
        return jsonify(result)

    except Exception as e:
        logger.error(
            f"Terjadi kesalahan saat menggabungkan keranjang user {user_id}: {e}",
            exc_info=True
        )
        return jsonify({
            'success': False, 
            'message': 'Gagal menyinkronkan keranjang.'
            }), 500


@api_bp.route('/checkout/prepare', methods=['POST'])
def prepare_guest_checkout():
    if 'user_id' in session:
        logger.warning(
            "Pengguna yang login mencoba mengakses endpoint checkout tamu."
        )
        return jsonify({
            'success': False, 
            'message': 'Endpoint ini hanya untuk tamu.'
            }), 403

    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        logger.info(
            f"session_id baru dibuat untuk checkout tamu: {session['session_id']}"
        )

    session_id = session['session_id']
    items_to_hold = request.get_json().get('items')

    logger.debug(
        f"Mempersiapkan checkout tamu untuk session_id: {session_id}. "
        f"Item: {items_to_hold}"
    )

    if not items_to_hold or not isinstance(items_to_hold, list):
        logger.warning(
            f"Data keranjang tidak valid untuk persiapan checkout tamu. Session ID: {session_id}"
        )
        return jsonify({
            'success': False, 
            'message': 'Data keranjang tidak valid.'
            }), 400

    formatted_items = []

    try:
        for item in items_to_hold:
            formatted_items.append({
                'id': item['id'],
                'name': item['name'],
                'size': item.get('size'),
                'variant_id': item.get('variant_id'),
                'quantity': item['quantity']
            })

    except KeyError as e:
        logger.error(
            f"Kunci data item keranjang tamu hilang: {e}. Session ID: {session_id}",
            exc_info=True
        )
        return jsonify({
            'success': False, 
            'message': 'Data item keranjang tidak lengkap.'
            }), 400

    try:
        hold_result = stock_service.hold_stock_for_checkout(None, session_id, formatted_items)
        if hold_result['success']:
            logger.info(
                f"Stok berhasil ditahan untuk checkout tamu. "
                f"Session ID: {session_id}. Kadaluarsa pada: {hold_result['expires_at']}"
            )
        else:
            logger.warning(
                f"Gagal menahan stok untuk checkout tamu. "
                f"Session ID: {session_id}. Alasan: {hold_result['message']}"
            )
        return jsonify(hold_result)

    except Exception as e:
        logger.error(
            f"Terjadi kesalahan saat menahan stok untuk checkout tamu. Session ID: {session_id}: {e}",
            exc_info=True
        )
        return jsonify({
            'success': False, 
            'message': 'Gagal memvalidasi stok.'
            }), 500