import random
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from app.core.db import get_db_connection
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class AuthService:


    def verify_user_login(self, username, password):
        logger.debug(f"Mencoba memverifikasi login untuk nama pengguna: {username}")
        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            user = cursor.fetchone()

            if user and check_password_hash(user['password'], password):
                logger.info(f"Login berhasil untuk pengguna: {username} (ID: {user['id']})")
                return user
            else:
                logger.warning(
                    f"Login gagal untuk nama pengguna: {username}. "
                    f"Pengguna ditemukan: {'Ya' if user else 'Tidak'}"
                )
                return None

        except Exception as e:
            logger.error(f"Kesalahan saat verifikasi login untuk {username}: {e}", exc_info=True)
            return None

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(f"Koneksi database ditutup untuk verify_user_login (nama pengguna: {username}).")


    def register_new_user(self, username, email, password):
        logger.debug(f"Mencoba mendaftarkan pengguna baru. Nama pengguna: {username}, Email: {email}")
        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                'SELECT id FROM users WHERE username = %s OR email = %s',
                (username, email)
            )
            user = cursor.fetchone()

            if user:
                logger.warning(
                    f"Pendaftaran gagal: Nama pengguna '{username}' atau Email '{email}' sudah ada."
                )
                return None

            hashed_password = generate_password_hash(password)
            cursor.execute(
                'INSERT INTO users (username, email, password) VALUES (%s, %s, %s)',
                (username, email, hashed_password)
            )

            new_user_id = cursor.lastrowid
            conn.commit()
            logger.info(
                f"Pengguna baru berhasil didaftarkan. Nama pengguna: {username}, "
                f"Email: {email}, ID: {new_user_id}"
            )

            cursor.execute('SELECT * FROM users WHERE id = %s', (new_user_id,))
            new_user = cursor.fetchone()
            return new_user if new_user else None

        except Exception as e:
            logger.error(f"Kesalahan saat pendaftaran pengguna baru untuk {username}: {e}", exc_info=True)
            if conn and conn.is_connected():
                conn.rollback()
            return None

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(f"Koneksi database ditutup untuk register_new_user (nama pengguna: {username}).")


    def register_guest_user(self, order_details, password):
        email = order_details.get('email')
        name = order_details.get('name')
        logger.debug(f"Mencoba mendaftarkan pengguna tamu. Email: {email}, Nama: {name}")
        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
            if cursor.fetchone():
                logger.warning(f"Pendaftaran tamu gagal: Email '{email}' sudah ada.")
                return None

            base_username = (
                name.lower().replace(' ', '')
                if name else f"guest_{random.randint(1000, 9999)}"
            )
            username = base_username

            cursor.execute('SELECT id FROM users WHERE username = %s', (username,))
            attempts = 0

            while cursor.fetchone() and attempts < 10:
                username = f"{base_username}{random.randint(10, 999)}"
                cursor.execute('SELECT id FROM users WHERE username = %s', (username,))
                attempts += 1

            if attempts >= 10:
                logger.error(f"Tidak dapat membuat nama pengguna unik untuk tamu berdasarkan '{base_username}'.")
                return None

            logger.debug(f"Nama pengguna dibuat untuk tamu: {username}")

            hashed_password = generate_password_hash(password)
            cursor.execute(
                """
                INSERT INTO users (
                    username, email, password, phone, address_line_1,
                    address_line_2, city, province, postal_code
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    username,
                    email,
                    hashed_password,
                    order_details.get('phone'),
                    order_details.get('address1'),
                    order_details.get('address2', ''),
                    order_details.get('city'),
                    order_details.get('province'),
                    order_details.get('postal_code'),
                ),
            )

            new_user_id = cursor.lastrowid
            conn.commit()
            logger.info(
                f"Pengguna tamu berhasil didaftarkan. Nama pengguna: {username}, "
                f"Email: {email}, ID: {new_user_id}"
            )

            cursor.execute('SELECT * FROM users WHERE id = %s', (new_user_id,))
            new_user = cursor.fetchone()
            return new_user if new_user else None

        except Exception as e:
            logger.error(f"Kesalahan saat pendaftaran pengguna tamu untuk email {email}: {e}", exc_info=True)
            if conn and conn.is_connected():
                conn.rollback()
            return None

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(f"Koneksi database ditutup untuk register_guest_user (email: {email}).")


    def handle_password_reset_request(self, email):
        logger.debug(f"Menangani permintaan reset kata sandi untuk email: {email}")
        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute('SELECT id, username FROM users WHERE email = %s', (email,))
            user = cursor.fetchone()

            if user:
                reset_token = str(uuid.uuid4())
                logger.info(
                    f"Reset kata sandi diminta untuk pengguna '{user['username']}' (ID: {user['id']})."
                )
                logger.info(
                    f"EMAIL SIMULASI: Mengirim email reset ke {email} dengan token: {reset_token}"
                )
            else:
                logger.info(f"Permintaan reset kata sandi untuk email yang tidak ada: {email}")

        except Exception as e:
            logger.error(f"Kesalahan menangani reset kata sandi untuk email {email}: {e}", exc_info=True)

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(f"Koneksi database ditutup untuk handle_password_reset_request (email: {email}).")


auth_service = AuthService()