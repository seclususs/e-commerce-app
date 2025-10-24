import os
from flask import send_from_directory, current_app, abort
from app.utils.logging_utils import get_logger
from . import image_bp

logger = get_logger(__name__)


@image_bp.route('/images/<path:filename>')
def serve_image(filename):
    image_dir = current_app.config.get('IMAGE_FOLDER')
    logger.debug(f"Mencoba menampilkan gambar: {filename}")

    if not image_dir:
        logger.error("IMAGE_FOLDER tidak dikonfigurasi dalam pengaturan aplikasi.")
        abort(404)

    if '..' in filename or filename.startswith('/'):
        logger.warning(f"Upaya traversal path terdeteksi dan diblokir: {filename}")
        abort(400)

    try:
        full_path = os.path.join(image_dir, filename)
        logger.info(f"Menampilkan gambar dari path: {full_path}")
        return send_from_directory(image_dir, filename)

    except FileNotFoundError:
        logger.warning(f"Gambar tidak ditemukan pada path: {full_path}")
        abort(404)

    except Exception as e:
        logger.error(f"Kesalahan saat menampilkan gambar {filename}: {e}", exc_info=True)
        abort(500)