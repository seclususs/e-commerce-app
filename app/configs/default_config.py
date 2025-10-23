import os

SECRET_KEY='2310-1140-1246'
IMAGE_FOLDER=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'images'))
ALLOWED_EXTENSIONS={'png', 'jpg', 'jpeg', 'gif', 'webp'}
DATABASE=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'database.db'))