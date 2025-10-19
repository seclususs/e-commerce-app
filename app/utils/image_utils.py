import os
import uuid
from PIL import Image
from flask import current_app

def allowed_file(filename):
    """Memeriksa apakah ekstensi file diizinkan."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_compressed_image(file_storage):
    """
    Menyimpan, mengompres, dan mengkonversi gambar ke format WebP.
    Juga memperbaiki masalah orientasi dari data EXIF.
    """
    if not file_storage or not allowed_file(file_storage.filename):
        return None
        
    try:
        # Buat nama file unik dan pastikan formatnya .webp
        filename_base = str(uuid.uuid4())
        filename = f"{filename_base}.webp"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

        # Buka gambar dari stream
        image = Image.open(file_storage.stream)

        # Perbaiki orientasi gambar berdasarkan data EXIF
        if hasattr(image, '_getexif') and image._getexif() is not None:
            exif = dict(image._getexif().items())
            orientation_key = 274  # Kunci untuk orientasi
            if orientation_key in exif:
                orientation = exif[orientation_key]
                if orientation == 3: image = image.rotate(180, expand=True)
                elif orientation == 6: image = image.rotate(270, expand=True)
                elif orientation == 8: image = image.rotate(90, expand=True)
        
        # Ubah ukuran gambar (thumbnail) dengan menjaga aspek rasio
        image.thumbnail((1080, 1080))
        
        # Simpan sebagai WebP dengan kualitas dan optimisasi
        image.save(filepath, 'WEBP', quality=85, optimize=True)
        
        return filename
    except Exception as e:
        # Catat error jika terjadi masalah saat pemrosesan
        print(f"Error processing image: {e}")
        return None