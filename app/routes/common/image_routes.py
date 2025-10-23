import os
from flask import send_from_directory, current_app, abort
from . import image_bp

@image_bp.route('/images/<path:filename>')
def serve_image(filename):
    image_dir = current_app.config.get('IMAGE_FOLDER')

    if not image_dir:
        print("IMAGE_FOLDER not configured")
        abort(404)

    if '..' in filename or filename.startswith('/'):
        print(f"Potential path traversal attempt: {filename}")
        abort(400)
    try:
        print(f"Attempting to serve image: {filename} from {image_dir}")
        return send_from_directory(image_dir, filename)
    except FileNotFoundError:
        print(f"Image not found: {os.path.join(image_dir, filename)}")
        abort(404)
    except Exception as e:
        print(f"Error serving image {filename}: {e}")
        abort(500)