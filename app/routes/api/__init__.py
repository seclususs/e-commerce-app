from flask import Blueprint

api_bp = Blueprint('api', __name__)

from . import cart_routes
from . import product_routes