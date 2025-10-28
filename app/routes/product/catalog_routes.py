from typing import Any, Dict, List, Optional

from flask import flash, render_template, request, jsonify

from app.core.db import get_content
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.services.products.category_service import category_service
from app.services.products.product_query_service import product_query_service
from app.utils.logging_utils import get_logger

from . import product_bp

logger = get_logger(__name__)


@product_bp.route("/products")
def products_page() -> str:
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    filters: Dict[str, Optional[str]] = {
        "search": request.args.get("search"),
        "category": request.args.get("category"),
        "sort": request.args.get("sort", "popularity"),
    }
    page_title = f"{get_content().get('app_name', 'App')} - Koleksi Produk"

    logger.debug(
        f"Mengakses halaman produk (AJAX: {is_ajax}) dengan filter: {filters}"
    )

    try:
        products: List[Dict[str, Any]] = (
            product_query_service.get_filtered_products(filters)
        )
        categories: List[Dict[str, Any]] = (
            category_service.get_all_categories()
        )
        logger.info(
            f"Berhasil mengambil {len(products)} produk dan "
            f"{len(categories)} kategori."
        )

        if is_ajax:
            html = render_template(
                "partials/public/_product_catalog.html",
                products=products,
                categories=categories,
                content=get_content(),
            )
            return jsonify(
                {"success": True, "html": html, "page_title": page_title}
            )
        else:
            return render_template(
                "public/product_catalog.html",
                products=products,
                categories=categories,
                content=get_content(),
            )

    except (DatabaseException, ServiceLogicError) as service_err:
        logger.error(
            f"Kesalahan service/DB saat memuat halaman produk: {service_err}",
            exc_info=True,
        )
        message = "Gagal memuat produk."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        flash(message, "danger")
        
    except Exception as e:
        logger.error(
            f"Kesalahan tak terduga saat memuat halaman produk: {e}",
            exc_info=True,
        )
        message = "Gagal memuat produk karena kesalahan tak terduga."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        flash(message, "danger")

    return render_template(
        "public/product_catalog.html",
        products=[],
        categories=[],
        content=get_content(),
    )