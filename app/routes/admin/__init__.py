import json
from flask import Blueprint
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)
logger.debug("Menginisialisasi blueprint Admin")
admin_bp = Blueprint('admin', __name__)

from . import dashboard_routes
from . import product_routes
from . import category_routes
from . import variant_routes
from . import order_routes
from . import report_routes
from . import setting_routes
from . import voucher_routes