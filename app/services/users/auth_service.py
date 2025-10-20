import random
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from db.db_config import get_db_connection

class AuthService:
    """
    Layanan yang menangani semua logika terkait otentikasi pengguna,
    seperti login dan registrasi.
    """

    def verify_user_login(self, username, password):
        """
        Memverifikasi kredensial pengguna.
        Mengembalikan data pengguna jika valid, None jika tidak.
        """
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            return dict(user)
        return None

    def register_new_user(self, username, email, password):
        """
        Mendaftarkan pengguna baru ke database.
        Mengembalikan data pengguna baru jika berhasil, None jika gagal (misal: username/email sudah ada).
        """
        conn = get_db_connection()
        try:
            user = conn.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email)).fetchone()
            if user:
                return None  # Pengguna sudah ada

            hashed_password = generate_password_hash(password)
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                (username, email, hashed_password)
            )
            new_user_id = cursor.lastrowid
            conn.commit()
            
            new_user = conn.execute('SELECT * FROM users WHERE id = ?', (new_user_id,)).fetchone()
            return dict(new_user) if new_user else None
        finally:
            conn.close()

    def register_guest_user(self, order_details, password):
        """
        Mendaftarkan pengguna dari data checkout tamu.
        """
        conn = get_db_connection()
        try:
            email = order_details['email']
            if conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone():
                return None  # Email sudah ada

            base_username = order_details['name'].lower().replace(' ', '')
            username = base_username
            while conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone():
                username = f"{base_username}{random.randint(10, 99)}"

            hashed_password = generate_password_hash(password)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, email, password, phone, address_line_1, address_line_2, city, province, postal_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (username, email, hashed_password, 
                  order_details.get('phone'), order_details.get('address1'), 
                  order_details.get('address2', ''), order_details.get('city'),
                  order_details.get('province'), order_details.get('postal_code')))
            
            new_user_id = cursor.lastrowid
            conn.commit()
            
            new_user = conn.execute('SELECT * FROM users WHERE id = ?', (new_user_id,)).fetchone()
            return dict(new_user) if new_user else None
        finally:
            conn.close()

    def handle_password_reset_request(self, email):
        """
        Menangani permintaan reset password. Dalam aplikasi nyata, ini akan
        menghasilkan token dan mengirim email. Di sini, kita hanya melakukan simulasi.
        """
        conn = get_db_connection()
        try:
            user = conn.execute('SELECT id, username FROM users WHERE email = ?', (email,)).fetchone()
            if user:
                # Simulasi: Cetak ke konsol server bahwa permintaan diterima
                reset_token = str(uuid.uuid4())
                print(f"PASSWORD RESET: Diminta untuk user '{user['username']}' (ID: {user['id']}).")
                print(f"SIMULASI EMAIL: Kirim email ke {email} dengan token: {reset_token}")
        finally:
            # Fungsi ini sengaja tidak mengembalikan apa pun untuk keamanan
            conn.close()

auth_service = AuthService()