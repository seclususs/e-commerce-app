from flask import Blueprint
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)
logger.debug("Menginisialisasi blueprint Pengguna")

user_bp = Blueprint('user', __name__)

from . import profile_routes