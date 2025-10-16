from werkzeug.security import check_password_hash, generate_password_hash
from database.db_config import get_db_connection

class UserService:
    """
    Layanan yang menangani semua logika bisnis terkait data pengguna.
    """
    def get_user_by_id(self, user_id):
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        return dict(user) if user else None

    def update_user_info(self, user_id, username, email):
        conn = get_db_connection()
        try:
            existing = conn.execute('SELECT id FROM users WHERE (username = ? OR email = ?) AND id != ?', 
                                    (username, email, user_id)).fetchone()
            if existing:
                return {'success': False, 'message': 'Username atau email sudah digunakan oleh akun lain.'}
            
            conn.execute('UPDATE users SET username = ?, email = ? WHERE id = ?', (username, email, user_id))
            conn.commit()
            return {'success': True, 'message': 'Informasi akun berhasil diperbarui.'}
        finally:
            conn.close()

    def change_user_password(self, user_id, current_password, new_password):
        conn = get_db_connection()
        try:
            user = conn.execute('SELECT password FROM users WHERE id = ?', (user_id,)).fetchone()
            if not user or not check_password_hash(user['password'], current_password):
                return {'success': False, 'message': 'Password saat ini salah.'}
            
            hashed_password = generate_password_hash(new_password)
            conn.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_password, user_id))
            conn.commit()
            return {'success': True, 'message': 'Password berhasil diubah.'}
        finally:
            conn.close()

    def update_user_address(self, user_id, address_data, conn=None):
        """Memperbarui alamat pengguna, dapat menggunakan koneksi db yang sudah ada."""
        # Menentukan apakah fungsi ini harus mengelola koneksi (buka/tutup/commit)
        is_external_conn = conn is not None
        if not is_external_conn:
            conn = get_db_connection()

        try:
            conn.execute("""
                UPDATE users SET phone = ?, address_line_1 = ?, address_line_2 = ?, 
                                 city = ?, province = ?, postal_code = ?
                WHERE id = ?
            """, (address_data.get('phone'), address_data.get('address1'), address_data.get('address2', ''),
                  address_data.get('city'), address_data.get('province'), address_data.get('postal_code'),
                  user_id))
            
            # Hanya commit jika fungsi ini yang membuat koneksi sendiri
            if not is_external_conn:
                conn.commit()

            return {'success': True, 'message': 'Alamat berhasil diperbarui.'}
        finally:
            # Hanya tutup koneksi jika fungsi ini yang membuatnya
            if not is_external_conn:
                conn.close()

user_service = UserService()