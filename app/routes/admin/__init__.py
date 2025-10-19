from flask import Blueprint

admin_bp = Blueprint('admin', __name__)
from . import dashboard_routes
from . import product_routes
from . import order_routes
from . import report_routes
from . import setting_routes
from . import voucher_routes