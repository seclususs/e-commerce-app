import mysql.connector
from flask import current_app, g
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


def get_db():
    if 'db' not in g:
        logger.debug('Mencoba membangun koneksi database.')
        try:
            g.db = mysql.connector.connect(
                host=current_app.config['MYSQL_HOST'],
                user=current_app.config['MYSQL_USER'],
                password=current_app.config['MYSQL_PASSWORD'],
                database=current_app.config['MYSQL_DB'],
                port=current_app.config['MYSQL_PORT']
            )
            g.cursor = g.db.cursor(dictionary=True)
            logger.info('Koneksi database berhasil dibuat.')
        except mysql.connector.Error as err:
            logger.error(
                f'Kesalahan saat menghubungkan ke MySQL: {err}', 
                exc_info=True
                )
            raise err
    else:
        logger.debug('Menggunakan kembali koneksi database yang sudah ada.')

    return g.cursor


def close_db(e=None):
    cursor = g.pop('cursor', None)
    if cursor is not None:
        try:
            cursor.close()
            logger.debug('Kursor database ditutup.')
        except Exception as ex:
            logger.error(
                f'Kesalahan saat menutup kursor: {ex}', 
                exc_info=True
                )

    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
            logger.info('Koneksi database ditutup.')
        except mysql.connector.Error as err:
            logger.error(
                f'Kesalahan saat menutup koneksi database: {err}', 
                exc_info=True
                )
    elif e:
        logger.debug(f'close_db dipanggil dengan pengecualian, tetapi tidak ditemukan koneksi DB aktif: {e}')
    else:
        logger.debug('close_db dipanggil, tetapi tidak ditemukan koneksi DB aktif.')


def get_content():
    logger.debug('Mengambil konten situs dari database.')
    cursor = get_db()
    cursor.execute('SELECT `key`, `value` FROM content')
    content_data = cursor.fetchall()
    logger.info(f'Berhasil mengambil {len(content_data)} item konten.')
    return {item['key']: item['value'] for item in content_data}


def get_db_connection():
    logger.debug('Mencoba membangun koneksi database independen baru.')
    try:
        conn = mysql.connector.connect(
            host=current_app.config['MYSQL_HOST'],
            user=current_app.config['MYSQL_USER'],
            password=current_app.config['MYSQL_PASSWORD'],
            database=current_app.config['MYSQL_DB'],
            port=current_app.config['MYSQL_PORT']
        )
        logger.info('Koneksi database independen berhasil dibuat.')
        return conn
    except mysql.connector.Error as err:
        logger.error(
            f'Kesalahan saat mendapatkan koneksi MySQL independen: {err}', 
            exc_info=True
            )
        raise err