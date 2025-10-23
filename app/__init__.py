import os
import sqlite3
from flask import Flask, g

from .routes.product import product_bp
from .routes.auth import auth_bp
from .routes.user import user_bp
from .routes.admin import admin_bp
from .routes.api import api_bp
from .routes.purchase import purchase_bp
from .routes.common import image_bp
from .utils.template_filters import register_template_filters
from .core.db import close_db

def create_app(test_config=None):
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    instance_path = os.path.join(project_root, 'database')

    app = Flask(__name__,
                instance_path=instance_path,
                static_folder=os.path.join(project_root, 'app', 'static'),
                template_folder=os.path.join(project_root, 'app', 'templates')
               )
    
    config_path = os.path.join(app.root_path, 'configs', 'default_config.py')
    app.config.from_pyfile(config_path)

    if test_config is not None:
        app.config.from_mapping(test_config)

    register_template_filters(app)

    app.register_blueprint(product_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(purchase_bp)
    app.register_blueprint(image_bp)

    try:
        os.makedirs(app.instance_path, exist_ok=True)
        if 'IMAGE_FOLDER' in app.config:
             os.makedirs(app.config['IMAGE_FOLDER'], exist_ok=True)
        else:
            print("Warning: IMAGE_FOLDER not found in config.")

    except OSError as e:
        print(f"Error creating instance path or image folder: {e}")

    app.teardown_appcontext(close_db)

    return app