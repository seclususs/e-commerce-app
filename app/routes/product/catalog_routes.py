from flask import render_template, request
from db.db_config import get_content
from services.products.product_query_service import product_query_service
from services.products.category_service import category_service
from . import product_bp

@product_bp.route('/products')
def products_page():
    """Menampilkan halaman katalog produk dengan fungsionalitas filter, sorting, dan pencarian."""
    
    # Kumpulkan parameter filter dari URL
    filters = {
        'search': request.args.get('search'),
        'category': request.args.get('category'),
        'sort': request.args.get('sort', 'popularity')
    }
    
    # Panggil service untuk mendapatkan produk yang sudah difilter
    products = product_query_service.get_filtered_products(filters)
    
    # Panggil service untuk mendapatkan semua kategori
    categories = category_service.get_all_categories()
    
    return render_template('public/product_catalog.html', 
                           products=products, 
                           categories=categories, 
                           content=get_content())