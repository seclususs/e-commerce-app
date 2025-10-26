from typing import Any, Dict, List

from flask import Response, jsonify, render_template, request

from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.services.products.product_query_service import product_query_service
from app.utils.logging_utils import get_logger

from . import api_bp

logger = get_logger(__name__)


@api_bp.route("/products")
def filter_products() -> Response:
    filters: Dict[str, Any] = {
        "search": request.args.get("search"),
        "category": request.args.get("category"),
        "sort": request.args.get("sort", "popularity"),
    }

    logger.debug(f"Menyaring produk dengan filter: {filters}")
    try:
        products: List[Any] = product_query_service.get_filtered_products(
            filters
        )
        html: str = render_template(
            "partials/_product_card.html", products=products
        )
        logger.info(f"Produk berhasil difilter. Jumlah: {len(products)}")
        return jsonify({"success": True, "html": html})
    
    except (DatabaseException, ServiceLogicError) as e:
        logger.error(
            f"Terjadi kesalahan service/DB saat memfilter produk: {e}",
            exc_info=True,
        )
        raise e
    
    except Exception as e:
        logger.error(
            f"Terjadi kesalahan tak terduga saat memfilter produk: {e}",
            exc_info=True,
        )
        raise ServiceLogicError("Gagal memfilter produk")