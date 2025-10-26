import os
from typing import Union

from flask import Response, current_app, send_from_directory
from werkzeug.exceptions import BadRequest, InternalServerError, NotFound

from app.exceptions.file_exceptions import (
    FileNotFoundError as CustomFileNotFoundError,
)
from app.utils.logging_utils import get_logger

from . import image_bp

logger = get_logger(__name__)


@image_bp.route("/images/<path:filename>")
def serve_image(filename: str) -> Response:
    image_dir: Union[str, None] = current_app.config.get("IMAGE_FOLDER")
    logger.debug(f"Mencoba menampilkan gambar: {filename}")
    if not image_dir:
        logger.error(
            "IMAGE_FOLDER tidak dikonfigurasi dalam pengaturan aplikasi."
        )
        raise NotFound("Konfigurasi folder gambar hilang.")

    if ".." in filename or filename.startswith("/"):
        log_msg: str = (
            f"Upaya traversal path terdeteksi dan diblokir: {filename}"
        )
        logger.warning(log_msg)
        raise BadRequest("Nama file tidak valid.")

    try:
        full_path: str = os.path.join(image_dir, filename)
        logger.info(f"Menampilkan gambar dari path: {full_path}")
        if not os.path.isfile(full_path):
            raise CustomFileNotFoundError(
                f"File gambar tidak ditemukan: {filename}"
            )
        return send_from_directory(image_dir, filename)
    
    except CustomFileNotFoundError as fnfe:
        logger.warning(f"Gambar tidak ditemukan pada path: {fnfe}")
        raise NotFound(str(fnfe))
    
    except Exception as e:
        error_msg: str = f"Kesalahan saat menampilkan gambar: {e}"
        logger.error(error_msg, exc_info=True)
        raise InternalServerError(error_msg)