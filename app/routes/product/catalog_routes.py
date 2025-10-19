from flask import render_template, request
from database.db_config import get_content
from services.product_service import product_service
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
    products = product_service.get_filtered_products(filters)
    
    # Panggil service untuk mendapatkan semua kategori
    categories = product_service.get_all_categories()
    
    return render_template('public/product_catalog.html', 
                           products=products, 
                           categories=categories, 
                           content=get_content())