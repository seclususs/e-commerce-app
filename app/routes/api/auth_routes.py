from flask import jsonify, request
from app.core.db import get_db_connection
from app.utils.logging_utils import get_logger
from . import api_bp

logger = get_logger(__name__)


@api_bp.route('/validate/username', methods=['POST'])
def validate_username():
    username = request.json.get('username')
    logger.debug(f"Memvalidasi username: {username}")

    if not username:
        logger.warning("Validasi gagal: kolom username kosong.")
        return jsonify({
            'available': False,
            'message': 'Username tidak boleh kosong.'
        })

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            'SELECT id FROM users WHERE username = %s',
            (username,)
        )
        user = cursor.fetchone()

        is_available = user is None
        message = (
            'Username tersedia.'
            if is_available else 'Username sudah digunakan.'
        )

        logger.info(
            f"Hasil validasi username '{username}': {message}"
        )

        return jsonify({
            'available': is_available,
            'message': message
        })

    except Exception as e:
        logger.error(
            f"Terjadi kesalahan saat memvalidasi username '{username}': {e}",
            exc_info=True
        )
        return jsonify({
            'available': False,
            'message': 'Gagal memeriksa ketersediaan username.'
        }), 500

    finally:
        cursor.close()
        conn.close()


@api_bp.route('/validate/email', methods=['POST'])
def validate_email():
    email = request.json.get('email')
    logger.debug(f"Memvalidasi email: {email}")

    if not email:
        logger.warning("Validasi gagal: kolom email kosong.")
        return jsonify({
            'available': False,
            'message': 'Email tidak boleh kosong.'
        })

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            'SELECT id FROM users WHERE email = %s',
            (email,)
        )
        user = cursor.fetchone()

        is_available = user is None
        message = (
            'Email tersedia.'
            if is_available else 'Email sudah terdaftar.'
        )

        logger.info(
            f"Hasil validasi email '{email}': {message}"
        )

        return jsonify({
            'available': is_available,
            'message': message
        })

    except Exception as e:
        logger.error(
            f"Terjadi kesalahan saat memvalidasi email '{email}': {e}",
            exc_info=True
        )
        return jsonify({
            'available': False,
            'message': 'Gagal memeriksa ketersediaan email.'
        }), 500

    finally:
        cursor.close()
        conn.close()