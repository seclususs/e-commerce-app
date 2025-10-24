from datetime import datetime
from decimal import Decimal # Import Decimal
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
            cursor.close()
            conn.close()
            logger.debug("Koneksi database ditutup untuk validate_and_calculate_voucher.")


voucher_service = VoucherService()