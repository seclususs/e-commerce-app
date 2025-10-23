from flask import Blueprint

image_bp = Blueprint('images', __name__)
from . import image_routes