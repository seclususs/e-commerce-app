from flask import Blueprint

product_bp = Blueprint('product', __name__)
from . import general_routes
from . import catalog_routes
from . import detail_routes