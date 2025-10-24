from flask import jsonify, request, render_template, url_for
from app.services.products.product_query_service import product_query_service
from app.utils.logging_utils import get_logger
from . import api_bp

logger = get_logger(__name__)


@api_bp.route('/products')
def filter_products():
    filters = {
        'search': request.args.get('search'),
        'category': request.args.get('category'),
        'sort': request.args.get('sort', 'popularity')
    }

    logger.debug(f"Menyaring produk dengan filter: {filters}")

    try:
        products = product_query_service.get_filtered_products(filters)
        html = render_template('partials/_product_card.html', products=products)
        logger.info(f"Produk berhasil difilter. Jumlah: {len(products)}")
        return jsonify({
            'html': html
            })

    except Exception as e:
        logger.error(f"Terjadi kesalahan saat memfilter produk: {e}", exc_info=True)
        return jsonify({
            'error': 'Gagal memfilter produk'
            }), 500