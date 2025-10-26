from flask import Blueprint

from app.utils.logging_utils import get_logger

logger = get_logger(__name__)
logger.debug("Menginisialisasi blueprint Produk")

product_bp = Blueprint("product", __name__)

from . import catalog_routes
from . import detail_routes
from . import general_routes