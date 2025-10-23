from flask import jsonify, request, render_template, url_for
from services.products.product_query_service import product_query_service
from . import api_bp


@api_bp.route('/products')
def filter_products():
    filters = {
        'search': request.args.get('search'),
        'category': request.args.get('category'),
        'sort': request.args.get('sort', 'popularity')
    }
    products = product_query_service.get_filtered_products(filters)
    html = render_template('partials/_product_card.html', products=products)
    return jsonify({'html': html})