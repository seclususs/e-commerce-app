from flask import render_template, request, jsonify

from app.core.db import get_content
from app.utils.logging_utils import get_logger

from . import purchase_bp

logger = get_logger(__name__)


@purchase_bp.route("/cart")
def cart_page() -> str:
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    logger.debug(f"Mengakses halaman keranjang (AJAX: {is_ajax}).")
    page_title = f"Keranjang Belanja - {get_content().get('app_name', 'App')}"

    try:
        if is_ajax:
            html = render_template("partials/purchase/_cart.html", content=get_content())
            return jsonify({
                "success": True,
                "html": html,
                "page_title": page_title
            })
        else:
            return render_template("purchase/cart.html", content=get_content())
        
    except Exception as e:
        logger.error(
            f"Error rendering cart page (AJAX: {is_ajax}): {e}", 
            exc_info=True
            )
        message = "Gagal memuat halaman keranjang."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        return render_template("purchase/cart.html", content=get_content())