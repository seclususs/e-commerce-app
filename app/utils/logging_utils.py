import logging
import logging.handlers
import os
from datetime import datetime
from flask import current_app


log_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
)
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_format = (
    '%(asctime)s - %(levelname)s - %(name)s - '
    '%(filename)s:%(lineno)d - %(message)s'
)
formatter = logging.Formatter(log_format)

current_date = datetime.now().strftime('%Y-%m-%d')
log_file = os.path.join(log_dir, f'app_{current_date}.log')

file_handler = logging.handlers.TimedRotatingFileHandler(
    log_file,
    when='midnight',
    interval=1,
    backupCount=7,
    encoding='utf-8'
)
file_handler.setFormatter(formatter)


console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)


root_logger = logging.getLogger()

if not root_logger.handlers:
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def setup_logging(app):
    is_debug = app.config.get('DEBUG_LOGGING', False)
    log_level = logging.DEBUG if is_debug else logging.INFO

    root_logger.setLevel(log_level)
    file_handler.setLevel(logging.DEBUG)
    console_handler.setLevel(log_level)

    if is_debug:
        logging.getLogger('werkzeug').setLevel(logging.DEBUG)
        logging.getLogger('mysql.connector').setLevel(logging.INFO)
    else:
        logging.getLogger('werkzeug').setLevel(logging.WARNING)
        logging.getLogger('mysql.connector').setLevel(logging.WARNING)

    get_logger(__name__).info(
        f"Logging dikonfigurasi. Mode debug: {is_debug}. Level diatur ke: {logging.getLevelName(log_level)}"
        )


def get_logger(name):
    return logging.getLogger(name)