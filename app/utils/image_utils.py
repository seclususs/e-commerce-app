import os
import uuid
from PIL import Image
from flask import current_app


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def save_compressed_image(file_storage):
    if not file_storage or not allowed_file(file_storage.filename):
        return None

    try:
        filename_base = str(uuid.uuid4())
        filename = f"{filename_base}.webp"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

        image = Image.open(file_storage.stream)

        if hasattr(image, '_getexif') and image._getexif() is not None:
            exif = dict(image._getexif().items())
            orientation_key = 274
            if orientation_key in exif:
                orientation = exif[orientation_key]
                if orientation == 3:
                    image = image.rotate(180, expand=True)
                elif orientation == 6:
                    image = image.rotate(270, expand=True)
                elif orientation == 8:
                    image = image.rotate(90, expand=True)

        image.thumbnail((1080, 1080))

        image.save(filepath, 'WEBP', quality=85, optimize=True)

        return filename
    except Exception as e:
        print(f"Error processing image: {e}")
        return None