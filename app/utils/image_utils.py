import os
import uuid
from PIL import Image
from flask import current_app
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


def allowed_file(filename):
    logger.debug(f"Mengecek apakah nama file diizinkan: {filename}")
    is_allowed = (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower()
        in current_app.config['ALLOWED_EXTENSIONS']
    )
    logger.debug(f"Nama file '{filename}' diizinkan: {is_allowed}")
    return is_allowed


def save_compressed_image(file_storage):
    if not file_storage or not file_storage.filename:
        logger.warning("Mencoba menyimpan file storage kosong.")
        return None

    if not allowed_file(file_storage.filename):
        logger.warning(f"Tipe file tidak diizinkan: {file_storage.filename}")
        return None

    try:
        filename_base = str(uuid.uuid4())
        filename = f"{filename_base}.webp"
        image_folder = current_app.config['IMAGE_FOLDER']
        filepath = os.path.join(image_folder, filename)

        logger.debug(f"Mencoba menyimpan gambar ke: {filepath}")
        os.makedirs(image_folder, exist_ok=True)

        image = Image.open(file_storage.stream)
        logger.debug(f"Membuka stream gambar untuk: {file_storage.filename}")

        if hasattr(image, '_getexif') and image._getexif() is not None:
            exif = dict(image._getexif().items())
            orientation_key = 274
            if orientation_key in exif:
                orientation = exif[orientation_key]
                logger.debug(f"Gambar memiliki tag EXIF orientasi: {orientation}")

                if orientation == 3:
                    image = image.rotate(180, expand=True)
                elif orientation == 6:
                    image = image.rotate(270, expand=True)
                elif orientation == 8:
                    image = image.rotate(90, expand=True)

        image.thumbnail((1080, 1080))
        logger.debug("Ukuran thumbnail gambar diubah.")

        image.save(filepath, 'WEBP', quality=85, optimize=True)
        logger.info(f"Berhasil menyimpan gambar terkompresi sebagai: {filename}")

        return filename

    except Exception as e:
        logger.error(f"Kesalahan memproses gambar {file_storage.filename}: {e}", exc_info=True)
        return None