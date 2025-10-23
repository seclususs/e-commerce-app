from flask import render_template, request
from db.db_config import get_content
from services.products.product_query_service import product_query_service
from services.products.category_service import category_service
from . import product_bp


@product_bp.route('/products')
def products_page():
    
    filters = {
        'search': request.args.get('search'),
        'category': request.args.get('category'),
        'sort': request.args.get('sort', 'popularity')
    }
    
    products = product_query_service.get_filtered_products(filters)
    
    categories = category_service.get_all_categories()
    
    return render_template('public/product_catalog.html', 
                           products=products, 
                           categories=categories, 
                           content=get_content())