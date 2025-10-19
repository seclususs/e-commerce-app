from flask import Blueprint

purchase_bp = Blueprint('purchase', __name__)
from . import checkout_routes
from . import order_routes
