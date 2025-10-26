import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from flask import Flask

from app.utils.logging_utils import get_logger, setup_logging

from .core.db import close_db
from .exceptions.error_handlers import register_error_handlers
from .routes.admin import admin_bp
from .routes.api import api_bp
from .routes.auth import auth_bp
from .routes.common import image_bp
from .routes.product import product_bp
from .routes.purchase import purchase_bp
from .routes.user import user_bp
from .utils.template_filters import register_template_filters

load_dotenv()
initial_logger = get_logger(__name__)
initial_logger.debug("Variabel lingkungan dimuat.")


def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    initial_logger.debug("Memulai pembuatan aplikasi Flask.")

    project_root: str = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir)
    )
    instance_path: str = os.path.join(project_root, "database")

    app = Flask(
        __name__,
        instance_path=instance_path,
        static_folder=os.path.join(project_root, "app", "static"),
        template_folder=os.path.join(project_root, "app", "templates"),
    )
    initial_logger.info("Instansi aplikasi Flask dibuat.")

    config_path: str = os.path.join(app.root_path, "configs", "default_config.py")
    app.config.from_pyfile(config_path)
    initial_logger.info(f"Konfigurasi dimuat dari {config_path}")

    if test_config is not None:
        app.config.from_mapping(test_config)
        initial_logger.info("Konfigurasi tes diterapkan.")

    with app.app_context():
        setup_logging(app)

    logger = get_logger(__name__)

    register_template_filters(app)
    logger.info("Filter template terdaftar.")

    register_error_handlers(app)
    logger.info("Handler error terdaftar.")

    app.register_blueprint(product_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(purchase_bp)
    app.register_blueprint(image_bp)
    logger.info("Blueprint terdaftar.")

    try:
        os.makedirs(app.instance_path, exist_ok=True)
        logger.debug(f"Memastikan path instansi ada: {app.instance_path}")

        if "IMAGE_FOLDER" in app.config:
            os.makedirs(app.config["IMAGE_FOLDER"], exist_ok=True)
            logger.debug(
                f"Memastikan folder gambar ada: {app.config['IMAGE_FOLDER']}"
            )
            
        else:
            logger.warning("IMAGE_FOLDER tidak ditemukan di konfigurasi.")

    except OSError as e:
        logger.critical(
            f"KRITIS: Kesalahan saat membuat path instansi atau folder gambar: {e}",
            exc_info=True,
        )

    app.teardown_appcontext(close_db)
    logger.debug("Fungsi teardown konteks aplikasi terdaftar.")

    logger.info("Pembuatan aplikasi Flask selesai.")
    return app