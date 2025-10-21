from flask import jsonify, request
from db.db_config import get_db_connection
from . import api_bp

@api_bp.route('/validate/username', methods=['POST'])
def validate_username():
    """Memeriksa ketersediaan username."""
    username = request.json.get('username')
    if not username:
        return jsonify({'available': False, 'message': 'Username tidak boleh kosong.'})
    
    conn = get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    
    is_available = user is None
    message = 'Username tersedia.' if is_available else 'Username sudah digunakan.'
    return jsonify({'available': is_available, 'message': message})

@api_bp.route('/validate/email', methods=['POST'])
def validate_email():
    """Memeriksa ketersediaan email."""
    email = request.json.get('email')
    if not email:
        return jsonify({'available': False, 'message': 'Email tidak boleh kosong.'})

    conn = get_db_connection()
    user = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()

    is_available = user is None
    message = 'Email tersedia.' if is_available else 'Email sudah terdaftar.'
    return jsonify({'available': is_available, 'message': message})