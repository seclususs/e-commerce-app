from flask import render_template

from app.core.db import get_content
from app.utils.logging_utils import get_logger

from . import purchase_bp

logger = get_logger(__name__)


@purchase_bp.route("/cart")
def cart_page() -> str:
    logger.debug("Mengakses halaman keranjang.")
    return render_template("purchase/cart.html", content=get_content())