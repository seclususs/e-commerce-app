from flask import Blueprint

from app.utils.logging_utils import get_logger

logger = get_logger(__name__)
logger.debug("Menginisialisasi blueprint Umum")

image_bp = Blueprint("images", __name__)

from . import image_routes