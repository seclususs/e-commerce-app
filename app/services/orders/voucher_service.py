from datetime import datetime
from app.core.db import get_db_connection


class VoucherService:

    def validate_and_calculate_voucher(self, code, subtotal):
        conn = get_db_connection()
        voucher = conn.execute("SELECT * FROM vouchers WHERE code = ? AND is_active = 1", (code.upper(),)).fetchone()
        conn.close()

        if not voucher:
            return {'success': False, 'message': 'Kode voucher tidak valid.'}

        now = datetime.now()
        if voucher['start_date'] and now < datetime.fromisoformat(voucher['start_date']):
            return {'success': False, 'message': 'Voucher belum berlaku.'}
        if voucher['end_date'] and now > datetime.fromisoformat(voucher['end_date']):
            return {'success': False, 'message': 'Voucher sudah kedaluwarsa.'}
        if voucher['max_uses'] is not None and voucher['use_count'] >= voucher['max_uses']:
            return {'success': False, 'message': 'Voucher sudah habis digunakan.'}
        if subtotal < voucher['min_purchase_amount']:
            return {'success': False, 'message': f"Minimal pembelian Rp {voucher['min_purchase_amount']:,.0f} untuk menggunakan voucher ini."}

        discount_amount = 0
        if voucher['type'] == 'PERCENTAGE':
            discount_amount = (voucher['value'] / 100) * subtotal
        elif voucher['type'] == 'FIXED_AMOUNT':
            discount_amount = voucher['value']

        discount_amount = min(discount_amount, subtotal)
        final_total = subtotal - discount_amount

        return {'success': True, 'discount_amount': discount_amount, 'final_total': final_total, 'message': 'Voucher berhasil diterapkan!'}


voucher_service = VoucherService()