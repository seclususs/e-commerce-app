from flask import Blueprint

from app.utils.logging_utils import get_logger

logger = get_logger(__name__)
logger.debug("Menginisialisasi blueprint Pembelian")

purchase_bp = Blueprint("purchase", __name__)

from . import cart_routes
from . import checkout_routes
from . import order_routes