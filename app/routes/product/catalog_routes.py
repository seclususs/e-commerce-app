from flask import render_template, request, flash
from app.core.db import get_content
from app.services.products.product_query_service import product_query_service
from app.services.products.category_service import category_service
from app.utils.logging_utils import get_logger
from . import product_bp

logger = get_logger(__name__)


@product_bp.route('/products')
def products_page():
    filters = {
        'search': request.args.get('search'),
        'category': request.args.get('category'),
        'sort': request.args.get('sort', 'popularity')
    }

    logger.debug(f"Mengakses halaman produk dengan filter: {filters}")

    try:
        products = product_query_service.get_filtered_products(filters)
        categories = category_service.get_all_categories()

        logger.info(
            f"Berhasil mengambil {len(products)} produk dan {len(categories)} kategori."
        )

        return render_template(
            'public/product_catalog.html',
            products=products,
            categories=categories,
            content=get_content()
        )

    except Exception as e:
        logger.error(f"Kesalahan saat memuat halaman produk: {e}", exc_info=True)
        flash("Gagal memuat produk.", "danger")

        return render_template(
            'public/product_catalog.html',
            products=[],
            categories=[],
            content=get_content()
        )