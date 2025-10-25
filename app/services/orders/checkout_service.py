import json
import uuid
import mysql.connector
from flask import session, redirect, url_for, flash
from app.core.db import get_db_connection
from app.services.users.user_service import user_service
from app.services.orders.order_service import order_service
from app.services.orders.stock_service import stock_service
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class CheckoutService:


    def _check_pending_order(self, user_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                '''
                SELECT id
                FROM orders
                WHERE user_id = %s
                AND status = 'Menunggu Pembayaran'
                ORDER BY order_date DESC
                LIMIT 1
                ''',
                (user_id,)
            )
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    def _validate_user_address(self, user):
        return all([
            user.get('phone'),
            user.get('address_line_1'),
            user.get('city'),
            user.get('province'),
            user.get('postal_code')
        ])

    def _check_guest_email_exists(self, email):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
            return cursor.fetchone() is not None
        finally:
            cursor.close()
            conn.close()

    def process_checkout(self, user_id, session_id, form_data, guest_cart_json):
        user = user_service.get_user_by_id(user_id) if user_id else None
        user_log_id = f"User {user_id}" if user_id else f"Session {session_id}"
        cart_data = None
        shipping_details = {}

        try:
            if user_id:
                if not user:
                    logger.error(f"ID Pengguna {user_id} tidak ditemukan selama checkout.")
                    session.clear()
                    return {'success': False, 'redirect': url_for('auth.login'), 'message': 'Terjadi kesalahan, pengguna tidak ditemukan.', 'flash_category': 'danger'}

                pending_order = self._check_pending_order(user_id)
                if pending_order:
                    held_items = stock_service.get_held_items_simple(user_id=user_id, session_id=None)
                    if not held_items:
                        logger.warning(f"Checkout pengguna {user_id}: Penahanan stok kedaluwarsa saat memiliki pesanan tertunda {pending_order['id']}.")
                        return {'success': False, 'redirect': url_for('purchase.cart_page'), 'message': 'Sesi checkout Anda berakhir karena stok tidak lagi ditahan. Silakan ulangi dari keranjang.', 'flash_category': 'warning'}

                    logger.info(f"Pengguna {user_id} memiliki pesanan tertunda {pending_order['id']}. Mengarahkan ke pembayaran.")
                    return {'success': False, 'redirect': url_for('purchase.payment_page', order_id=pending_order['id']), 'message': 'Anda memiliki pesanan yang belum dibayar. Silakan selesaikan pembayaran.', 'flash_category': 'info'}

                if not self._validate_user_address(user):
                    logger.warning(f"Checkout gagal untuk pengguna {user_id}: Alamat pengiriman belum lengkap.")
                    return {'success': False, 'redirect': url_for('purchase.edit_address'), 'message': 'Alamat pengiriman belum lengkap. Mohon perbarui di profil Anda.', 'flash_category': 'danger'}

                shipping_details = {
                    'name': user.get('username'),
                    'phone': user.get('phone'),
                    'address1': user.get('address_line_1'),
                    'address2': user.get('address_line_2', ''),
                    'city': user.get('city'),
                    'province': user.get('province'),
                    'postal_code': user.get('postal_code')
                }
                logger.debug(f"Detail pengiriman pengguna {user_id}: {shipping_details}")

            else:
                if not guest_cart_json or guest_cart_json == '{}':
                    logger.warning(f"Checkout tamu gagal: Data keranjang kosong. Session ID: {session_id}")
                    return {'success': False, 'redirect': url_for('purchase.cart_page'), 'message': 'Keranjang Anda kosong.', 'flash_category': 'danger'}
                try:
                    cart_data = json.loads(guest_cart_json)
                    logger.debug(f"Data keranjang tamu dimuat: {cart_data}")
                except json.JSONDecodeError:
                    logger.error(f"Checkout tamu gagal: JSON cart_data tidak valid. Session ID: {session_id}", exc_info=True)
                    return {'success': False, 'redirect': url_for('purchase.cart_page'), 'message': 'Data keranjang tidak valid.', 'flash_category': 'danger'}

                email_for_order = form_data.get('email')
                if not email_for_order:
                    logger.warning(f"Checkout tamu gagal: Email tidak diisi. Session ID: {session_id}")
                    return {'success': False, 'redirect': url_for('purchase.checkout'), 'message': 'Email wajib diisi untuk checkout.', 'flash_category': 'danger'}

                if self._check_guest_email_exists(email_for_order):
                    logger.warning(f"Checkout tamu gagal: Email {email_for_order} sudah terdaftar. Session ID: {session_id}")
                    return {'success': False, 'redirect': url_for('auth.login', next=url_for('purchase.checkout')), 'message': 'Email sudah terdaftar. Silakan login untuk melanjutkan.', 'flash_category': 'danger'}

                shipping_details = {
                    'name': form_data['full_name'],
                    'phone': form_data['phone'],
                    'address1': form_data['address_line_1'],
                    'address2': form_data.get('address_line_2', ''),
                    'city': form_data['city'],
                    'province': form_data['province'],
                    'postal_code': form_data['postal_code']
                }
                session['guest_order_details'] = {'email': email_for_order, **shipping_details}
                logger.debug(f"Detail pengiriman tamu {session_id}: {shipping_details}")

            payment_method = form_data['payment_method']
            voucher_code = form_data.get('voucher_code') or None
            try:
                shipping_cost = float(form_data.get('shipping_cost', 0))
            except ValueError:
                logger.warning(f"Nilai shipping_cost tidak valid: {form_data.get('shipping_cost')}. Diubah ke 0.")
                shipping_cost = 0.0

            logger.info(
                f"Membuat pesanan untuk {user_log_id}. "
                f"Metode: {payment_method}, Voucher: {voucher_code}, Pengiriman: {shipping_cost}"
            )

            result = order_service.create_order(
                user_id,
                session_id if not user_id else None,
                cart_data,
                shipping_details,
                payment_method,
                voucher_code,
                shipping_cost
            )

            if result['success']:
                order_id = result['order_id']
                logger.info(f"Pesanan #{order_id} berhasil dibuat untuk {user_log_id}.")

                if not user_id:
                    session['guest_order_id'] = order_id

                if payment_method == 'COD':
                    return {'success': True, 'redirect': url_for('purchase.order_success'), 'message': f"Pesanan #{order_id} (COD) berhasil dibuat!", 'flash_category': 'success'}
                else:
                    logger.info(f"Mengarahkan {user_log_id} ke pembayaran untuk pesanan #{order_id}")
                    return {'success': True, 'redirect': url_for('purchase.payment_page', order_id=order_id)}
            else:
                logger.error(f"Pembuatan pesanan gagal untuk {user_log_id}. Alasan: {result.get('message', 'Kesalahan tidak diketahui')}")
                return {'success': False, 'redirect': url_for('purchase.cart_page'), 'message': result.get('message', 'Gagal membuat pesanan.'), 'flash_category': 'danger'}

        except mysql.connector.Error as db_err:
            logger.error(f"Kesalahan database selama checkout untuk {user_log_id}: {db_err}", exc_info=True)
            return {'success': False, 'redirect': url_for('purchase.cart_page'), 'message': 'Terjadi kesalahan database saat memproses checkout.', 'flash_category': 'danger'}
        except Exception as e:
            logger.error(f"Kesalahan tak terduga selama checkout untuk {user_log_id}: {e}", exc_info=True)
            return {'success': False, 'redirect': url_for('purchase.cart_page'), 'message': 'Terjadi kesalahan tak terduga saat checkout.', 'flash_category': 'danger'}


checkout_service = CheckoutService()