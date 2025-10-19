import os
import json
from flask import Flask

from routes.product import product_bp 
from routes.auth import auth_bp
from routes.user import user_bp
from routes.admin import admin_bp
from routes.api import api_bp
from routes.purchase import purchase_bp

def create_app():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    instance_path = os.path.join(project_root, 'instance')
    
    app = Flask(__name__, instance_path=instance_path)

    # Konfigurasi aplikasi
    app.config.from_mapping(
        SECRET_KEY='2310-1140-1246',
        UPLOAD_FOLDER=os.path.join(app.root_path, 'static', 'uploads'),
        ALLOWED_EXTENSIONS={'png', 'jpg', 'jpeg', 'gif', 'webp'},
        # Menentukan path database di dalam folder instance yang sudah benar
        DATABASE=os.path.join(app.instance_path, 'database.db')
    )

    # Filter kustom untuk format Rupiah di Jinja2
    @app.template_filter('rupiah')
    def format_rupiah(value):
        try:
            val = float(value)
            # Format sebagai mata uang Rupiah
            return f"Rp {val:,.0f}".replace(',', '.')
        except (ValueError, TypeError, AttributeError):
            return "Rp 0"

    # Filter kustom untuk menghitung persentase diskon
    @app.template_filter('percentage')
    def format_percentage(part, whole):
        try:
            part = float(part)
            whole = float(whole)
            if whole == 0:
                return 0
            return round(100 * (whole - part) / whole)
        except (ValueError, TypeError):
            return 0
            
    @app.template_filter('tojson_safe')
    def tojson_safe_filter(obj):
        return json.dumps(obj)

    # Registrasi semua blueprint
    app.register_blueprint(product_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(purchase_bp)

    # Pastikan folder instance dan upload ada saat aplikasi berjalan
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8080, debug=True)