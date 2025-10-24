from flask import Blueprint
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)
logger.debug("Menginisialisasi blueprint Auth")

auth_bp = Blueprint('auth', __name__)

from . import login_routes
from . import register_routes
from . import logout_routes
from . import forgot_password_routes