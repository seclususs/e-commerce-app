from functools import wraps
from typing import Callable

from flask import session

from app.exceptions.api_exceptions import AuthError, PermissionDeniedError
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


def login_required(f: Callable) -> Callable:
    @wraps(f)
    def decorated_function(*args, **kwargs):
        
        if "user_id" not in session:
            logger.debug(
                f"Akses ditolak untuk rute {f.__name__}: "
                f"Pengguna belum login."
            )
            raise AuthError("Anda harus login untuk mengakses halaman ini.")
        
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f: Callable) -> Callable:
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if not session.get("is_admin"):
            user_id: str = session.get("user_id", "Unknown")
            logger.warning(
                f"Akses admin ditolak untuk rute {f.__name__}. "
                f"ID Pengguna: {user_id} bukan admin."
            )
            raise PermissionDeniedError(
                "Hanya admin yang dapat mengakses halaman ini."
            )
        
        return f(*args, **kwargs)

    return decorated_function