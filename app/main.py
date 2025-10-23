import os
from flask import Flask

from routes.product import product_bp
from routes.auth import auth_bp
from routes.user import user_bp
from routes.admin import admin_bp
from routes.api import api_bp
from routes.purchase import purchase_bp

from utils.template_filters import register_template_filters

def create_app():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    instance_path = os.path.join(project_root, 'database')

    app = Flask(__name__, instance_path=instance_path)

    app.config.from_mapping(
        SECRET_KEY='2310-1140-1246',
        UPLOAD_FOLDER=os.path.join(app.root_path, 'static', 'uploads'),
        ALLOWED_EXTENSIONS={'png', 'jpg', 'jpeg', 'gif', 'webp'},
        DATABASE=os.path.join(app.instance_path, 'database.db')
    )

    register_template_filters(app)

    app.register_blueprint(product_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(purchase_bp)

    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError as e:
        print(f"Error creating instance path: {e}")

    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    except OSError as e:
        print(f"Error creating upload folder: {e}")

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8080, debug=True)