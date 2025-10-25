from datetime import datetime
from decimal import Decimal
import mysql.connector
from app.core.db import get_db_connection
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class VoucherService:


    def validate_and_calculate_voucher(self, code, subtotal):
        upper_code = code.upper()
        subtotal_decimal = Decimal(str(subtotal))
        logger.debug(f"Memvalidasi kode voucher: {upper_code} untuk subtotal: {subtotal_decimal}")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(
                "SELECT * FROM vouchers WHERE code = %s AND is_active = 1",
                (upper_code,)
            )
            voucher = cursor.fetchone()

            if not voucher:
                logger.info(
                    f"Validasi voucher gagal: Kode '{upper_code}' tidak ditemukan atau tidak aktif."
                )
                return {'success': False, 'message': 'Kode voucher tidak valid.'}

            logger.debug(f"Voucher '{upper_code}' ditemukan: {voucher}")
            now = datetime.now()

            if voucher['start_date'] and now < voucher['start_date']:
                logger.info(
                    f"Validasi voucher '{upper_code}' gagal: Belum berlaku "
                    f"(dimulai {voucher['start_date']})."
                )
                return {'success': False, 'message': 'Voucher belum berlaku.'}

            if voucher['end_date'] and now > voucher['end_date']:
                logger.info(
                    f"Validasi voucher '{upper_code}' gagal: Kedaluwarsa "
                    f"(berakhir {voucher['end_date']})."
                )
                return {'success': False, 'message': 'Voucher sudah kedaluwarsa.'}

            if voucher['max_uses'] is not None and voucher['use_count'] >= voucher['max_uses']:
                logger.info(
                    f"Validasi voucher '{upper_code}' gagal: Batas penggunaan "
                    f"({voucher['max_uses']}) tercapai."
                )
                return {'success': False, 'message': 'Voucher sudah habis digunakan.'}

            min_purchase_decimal = Decimal(str(voucher.get('min_purchase_amount', 0)))
            if subtotal_decimal < min_purchase_decimal:
                min_purchase_formatted = f"Rp {min_purchase_decimal:,.0f}".replace(',', '.')
                logger.info(
                    f"Validasi voucher '{upper_code}' gagal: Subtotal {subtotal_decimal} "
                    f"kurang dari pembelian minimum {min_purchase_decimal}."
                )
                return {
                    'success': False,
                    'message': f"Minimal pembelian {min_purchase_formatted} untuk menggunakan voucher ini."
                }

            discount_amount = Decimal('0')
            voucher_type = voucher['type']
            voucher_value_decimal = Decimal(str(voucher['value']))

            if voucher_type == 'PERCENTAGE':
                discount_amount = (voucher_value_decimal / Decimal('100')) * subtotal_decimal
                discount_amount = discount_amount.quantize(Decimal('0.01'))
                logger.debug(
                    f"Menghitung diskon persentase untuk '{upper_code}': "
                    f"({voucher_value_decimal}% dari {subtotal_decimal}) = {discount_amount}"
                )
            elif voucher_type == 'FIXED_AMOUNT':
                discount_amount = voucher_value_decimal
                logger.debug(
                    f"Menerapkan diskon jumlah tetap untuk '{upper_code}': {discount_amount}"
                )
            else:
                logger.error(f"Tipe voucher '{voucher_type}' untuk kode '{upper_code}' tidak dikenal.")
                return {'success': False, 'message': 'Tipe voucher tidak dikenal.'}

            discount_amount = min(discount_amount, subtotal_decimal)
            final_total = subtotal_decimal - discount_amount

            logger.info(
                f"Voucher '{upper_code}' berhasil divalidasi. "
                f"Diskon: {discount_amount}, Total Akhir: {final_total}"
            )

            return {
                'success': True,
                'discount_amount': float(discount_amount),
                'final_total': float(final_total),
                'message': 'Voucher berhasil diterapkan!'
            }

        except Exception as e:
            logger.error(f"Kesalahan saat memvalidasi voucher '{upper_code}': {e}", exc_info=True)
            return {'success': False, 'message': 'Gagal memvalidasi voucher karena kesalahan server.'}

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug("Koneksi database ditutup untuk validate_and_calculate_voucher.")


    def get_all_vouchers(self):
        logger.debug("Mengambil semua data voucher dari service.")
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM vouchers ORDER BY id DESC")
            vouchers = cursor.fetchall()
            logger.info(f"Berhasil mengambil {len(vouchers)} voucher dari service.")
            return vouchers
        except Exception as e:
            logger.error(f"Kesalahan service saat mengambil semua voucher: {e}", exc_info=True)
            raise
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug("Koneksi database ditutup untuk get_all_vouchers.")


    def add_voucher(self, code, v_type, value, min_purchase, max_uses):
        upper_code = code.upper().strip()
        logger.debug(
            f"Service: Mencoba menambahkan voucher. Kode: {upper_code}, Tipe: {v_type}, "
            f"Nilai: {value}, Minimal Belanja: {min_purchase}, Maksimum Penggunaan: {max_uses}"
        )

        if not upper_code or not v_type or not value:
            logger.warning("Service: Gagal menambahkan voucher: Kolom wajib belum diisi.")
            return {'success': False, 'message': 'Kode, Tipe, dan Nilai tidak boleh kosong.'}

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """
                INSERT INTO vouchers (code, type, value, min_purchase_amount, max_uses)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (upper_code, v_type, value, min_purchase or 0, max_uses or None)
            )
            new_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Service: Voucher '{upper_code}' berhasil ditambahkan dengan ID: {new_id}")

            cursor.execute("SELECT * FROM vouchers WHERE id = %s", (new_id,))
            new_voucher = cursor.fetchone()

            return {
                'success': True,
                'message': f'Voucher "{upper_code}" berhasil ditambahkan.',
                'data': new_voucher
            }
        except mysql.connector.IntegrityError:
            conn.rollback()
            logger.warning(f"Service: Gagal menambahkan voucher: kode '{upper_code}' sudah ada.")
            return {'success': False, 'message': f'Kode voucher "{upper_code}" sudah terdaftar.'}
        except Exception as e:
            conn.rollback()
            logger.error(
                f"Service: Terjadi kesalahan saat menambahkan voucher '{upper_code}': {e}",
                exc_info=True
            )
            return {'success': False, 'message': 'Gagal menambahkan voucher karena kesalahan server.'}
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug("Koneksi database ditutup untuk add_voucher.")


    def delete_voucher_by_id(self, voucher_id):
        logger.debug(f"Service: Mencoba menghapus voucher dengan ID: {voucher_id}")
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM vouchers WHERE id = %s", (voucher_id,))
            conn.commit()

            if cursor.rowcount > 0:
                logger.info(f"Service: Voucher ID {voucher_id} berhasil dihapus.")
                return {'success': True, 'message': 'Voucher berhasil dihapus.'}
            else:
                logger.warning(f"Service: Voucher ID {voucher_id} tidak ditemukan saat akan dihapus.")
                return {'success': False, 'message': 'Voucher tidak ditemukan.'}
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(
                f"Service: Terjadi kesalahan saat menghapus voucher ID {voucher_id}: {e}",
                exc_info=True
            )
            return {'success': False, 'message': 'Gagal menghapus voucher.'}
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug("Koneksi database ditutup untuk delete_voucher_by_id.")


    def toggle_voucher_status(self, voucher_id):
        logger.debug(f"Service: Mencoba mengubah status voucher dengan ID: {voucher_id}")
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT is_active FROM vouchers WHERE id = %s", (voucher_id,))
            voucher = cursor.fetchone()

            if voucher:
                new_status = not voucher['is_active']
                cursor.execute(
                    "UPDATE vouchers SET is_active = %s WHERE id = %s",
                    (new_status, voucher_id)
                )
                conn.commit()
                status_text = "Aktif" if new_status else "Tidak Aktif"
                logger.info(
                    f"Service: Status voucher ID {voucher_id} berhasil diubah menjadi {status_text}."
                )
                return {
                    'success': True,
                    'message': f'Status voucher berhasil diubah menjadi {status_text}.',
                    'data': {'is_active': new_status}
                }
            else:
                logger.warning(f"Service: Voucher ID {voucher_id} tidak ditemukan untuk diubah statusnya.")
                return {'success': False, 'message': 'Voucher tidak ditemukan.'}
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(
                f"Service: Terjadi kesalahan saat mengubah status voucher ID {voucher_id}: {e}",
                exc_info=True
            )
            return {'success': False, 'message': 'Gagal mengubah status voucher.'}
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug("Koneksi database ditutup untuk toggle_voucher_status.")


voucher_service = VoucherService()