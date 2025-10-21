from flask import jsonify, request, render_template, url_for
from services.products.product_query_service import product_query_service
from . import api_bp

@api_bp.route('/products')
def filter_products():
    """
    Endpoint untuk pemfilteran produk secara asinkron.
    Mengembalikan HTML kartu produk yang sudah dirender.
    """
    # Kumpulkan parameter filter dari URL
    filters = {
        'search': request.args.get('search'),
        'category': request.args.get('category'),
        'sort': request.args.get('sort', 'popularity')
    }
    
    # Panggil service untuk mendapatkan produk yang sudah difilter
    products = product_query_service.get_filtered_products(filters)
    
    # Render HTML di sisi server dan kirimkan sebagai JSON
    html = render_template('partials/_product_card.html', products=products)
    return jsonify({'html': html})