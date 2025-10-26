from typing import Any, Dict, List, Optional

from flask import flash, render_template, request

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
    filters: Dict[str, Optional[str]] = {
        "search": request.args.get("search"),
        "category": request.args.get("category"),
        "sort": request.args.get("sort", "popularity"),
    }

    logger.debug(f"Mengakses halaman produk dengan filter: {filters}")
    
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
        flash("Gagal memuat produk.", "danger")

    except Exception as e:
        logger.error(
            f"Kesalahan tak terduga saat memuat halaman produk: {e}",
            exc_info=True,
        )
        flash("Gagal memuat produk karena kesalahan tak terduga.", "danger")

    return render_template(
        "public/product_catalog.html",
        products=[],
        categories=[],
        content=get_content(),
    )