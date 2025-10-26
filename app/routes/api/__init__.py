from flask import Blueprint

from app.utils.logging_utils import get_logger

logger = get_logger(__name__)
logger.debug("Menginisialisasi blueprint API")

api_bp = Blueprint("api", __name__)

from . import auth_routes
from . import cart_routes
from . import payment_routes
from . import product_routes
from . import scheduler_routes
from . import voucher_routes