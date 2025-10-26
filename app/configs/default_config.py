import os
from typing import Optional, Set

IMAGE_FOLDER: str = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "database", "images")
)

ALLOWED_EXTENSIONS: Set[str] = {"png", "jpg", "jpeg", "gif", "webp"}

SECRET_KEY: Optional[str] = os.environ.get("SECRET_KEY")
MYSQL_HOST: Optional[str] = os.environ.get("MYSQL_HOST")
MYSQL_USER: Optional[str] = os.environ.get("MYSQL_USER")
MYSQL_PASSWORD: Optional[str] = os.environ.get("MYSQL_PASSWORD")
MYSQL_DB: Optional[str] = os.environ.get("MYSQL_DB")
MYSQL_PORT: Optional[str] = os.environ.get("MYSQL_PORT")
DEBUG_LOGGING: bool = os.environ.get("DEBUG_LOGGING", "False").lower() == "true"