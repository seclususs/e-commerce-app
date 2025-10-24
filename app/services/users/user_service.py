from werkzeug.security import check_password_hash, generate_password_hash
import mysql.connector
from app.core.db import get_db_connection
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class UserService:


    def get_user_by_id(self, user_id):
        logger.debug(f"Mengambil pengguna berdasarkan ID: {user_id}")
        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
            user = cursor.fetchone()

            if user:
                logger.info(f"Pengguna ditemukan untuk ID: {user_id}")
            else:
                logger.warning(f"Pengguna tidak ditemukan untuk ID: {user_id}")

            return user if user else None

        except Exception as e:
            logger.error(f"Kesalahan saat mengambil pengguna ID {user_id}: {e}", exc_info=True)
            return None

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(f"Koneksi database ditutup untuk get_user_by_id (ID: {user_id}).")


    def update_user_info(self, user_id, username, email):
        logger.debug(
            f"Mencoba memperbarui info pengguna untuk ID: {user_id}. "
            f"Nama pengguna baru: {username}, Email baru: {email}"
        )
        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id FROM users WHERE (username = %s OR email = %s) AND id != %s',
                (username, email, user_id)
            )
            existing = cursor.fetchone()

            if existing:
                logger.warning(
                    f"Pembaruan gagal untuk pengguna {user_id}: Nama pengguna '{username}' "
                    f"atau email '{email}' sudah digunakan."
                )
                return {'success': False, 'message': 'Username atau email sudah digunakan oleh akun lain.'}

            cursor.execute(
                'UPDATE users SET username = %s, email = %s WHERE id = %s',
                (username, email, user_id)
            )
            conn.commit()

            logger.info(f"Info pengguna berhasil diperbarui untuk ID: {user_id}")
            return {'success': True, 'message': 'Informasi akun berhasil diperbarui.'}

        except Exception as e:
            logger.error(f"Kesalahan saat memperbarui info pengguna untuk ID {user_id}: {e}", exc_info=True)
            if conn and conn.is_connected():
                conn.rollback()
            return {'success': False, 'message': 'Gagal memperbarui informasi akun.'}

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(f"Koneksi database ditutup untuk update_user_info (ID: {user_id}).")


    def change_user_password(self, user_id, current_password, new_password):
        logger.debug(f"Mencoba mengubah kata sandi untuk pengguna ID: {user_id}")
        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT password FROM users WHERE id = %s', (user_id,))
            user = cursor.fetchone()

            if not user or not check_password_hash(user['password'], current_password):
                logger.warning(f"Perubahan kata sandi gagal untuk pengguna {user_id}: Kata sandi saat ini salah.")
                return {'success': False, 'message': 'Password saat ini salah.'}

            hashed_password = generate_password_hash(new_password)
            cursor.execute('UPDATE users SET password = %s WHERE id = %s', (hashed_password, user_id))
            conn.commit()

            logger.info(f"Kata sandi berhasil diubah untuk pengguna ID: {user_id}")
            return {'success': True, 'message': 'Password berhasil diubah.'}

        except Exception as e:
            logger.error(f"Kesalahan saat mengubah kata sandi untuk pengguna ID {user_id}: {e}", exc_info=True)
            if conn and conn.is_connected():
                conn.rollback()
            return {'success': False, 'message': 'Gagal mengubah password.'}

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(f"Koneksi database ditutup untuk change_user_password (ID: {user_id}).")


    def update_user_address(self, user_id, address_data, conn=None):
        logger.debug(f"Mencoba memperbarui alamat untuk pengguna ID: {user_id}. Data: {address_data}")
        is_external_conn = conn is not None
        cursor = None

        if not is_external_conn:
            logger.debug("Membuat koneksi DB baru untuk update_user_address.")
            conn = get_db_connection()

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE users
                SET phone = %s, address_line_1 = %s, address_line_2 = %s,
                    city = %s, province = %s, postal_code = %s
                WHERE id = %s
                """,
                (
                    address_data.get('phone'),
                    address_data.get('address1'),
                    address_data.get('address2', ''),
                    address_data.get('city'),
                    address_data.get('province'),
                    address_data.get('postal_code'),
                    user_id,
                )
            )

            if not is_external_conn:
                conn.commit()

            logger.info(
                f"Alamat berhasil diperbarui untuk pengguna ID: {user_id}. "
                f"Baris terpengaruh: {cursor.rowcount}"
            )
            return {'success': True, 'message': 'Alamat berhasil diperbarui.'}

        except Exception as e:
            logger.error(f"Kesalahan saat memperbarui alamat untuk pengguna ID {user_id}: {e}", exc_info=True)
            if not is_external_conn and conn and conn.is_connected():
                conn.rollback()
            return {'success': False, 'message': 'Gagal memperbarui alamat.'}

        finally:
            if cursor:
                cursor.close()

            if not is_external_conn and conn and conn.is_connected():
                conn.close()
                logger.debug(f"Koneksi DB ditutup untuk update_user_address (ID: {user_id}).")
            elif is_external_conn:
                logger.debug(f"Kursor ditutup untuk update_user_address (ID: {user_id}, koneksi eksternal).")


user_service = UserService()