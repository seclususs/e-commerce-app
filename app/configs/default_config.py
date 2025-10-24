import os


IMAGE_FOLDER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'images')
)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

SECRET_KEY = os.environ.get('SECRET_KEY')
MYSQL_HOST = os.environ.get('MYSQL_HOST')
MYSQL_USER = os.environ.get('MYSQL_USER')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD')
MYSQL_DB = os.environ.get('MYSQL_DB')
MYSQL_PORT = os.environ.get('MYSQL_PORT')
DEBUG_LOGGING = os.environ.get('DEBUG_LOGGING', 'False').lower() == 'true'