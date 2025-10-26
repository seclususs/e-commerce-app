import logging
import logging.handlers
import os
from datetime import datetime

from flask import Flask

log_dir: str = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "logs")
)

if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_format: str = (
    "%(asctime)s - %(levelname)s - %(name)s - "
    "%(filename)s:%(lineno)d - %(message)s"
)
formatter: logging.Formatter = logging.Formatter(log_format)
current_date: str = datetime.now().strftime("%Y-%m-%d")
log_file: str = os.path.join(log_dir, f"app_{current_date}.log")
file_handler: logging.handlers.TimedRotatingFileHandler = (
    logging.handlers.TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
)

file_handler.setFormatter(formatter)

console_handler: logging.StreamHandler = logging.StreamHandler()
console_handler.setFormatter(formatter)

root_logger: logging.Logger = logging.getLogger()

if not root_logger.handlers:
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def setup_logging(app: Flask) -> None:
    is_debug: bool = app.config.get("DEBUG_LOGGING", False)
    log_level: int = logging.DEBUG if is_debug else logging.INFO

    root_logger.setLevel(log_level)
    file_handler.setLevel(logging.DEBUG)
    console_handler.setLevel(log_level)

    if is_debug:
        logging.getLogger("werkzeug").setLevel(logging.DEBUG)
        logging.getLogger("mysql.connector").setLevel(logging.INFO)

    else:
        logging.getLogger("werkzeug").setLevel(logging.WARNING)
        logging.getLogger("mysql.connector").setLevel(logging.WARNING)

    get_logger(__name__).info(
        f"Logging dikonfigurasi. Mode debug: {is_debug}. "
        f"Level diatur ke: {logging.getLevelName(log_level)}"
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)