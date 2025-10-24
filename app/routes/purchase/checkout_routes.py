import json
import uuid
import mysql.connector
from flask import render_template, request, session, redirect, url_for, flash
from app.core.db import get_db_connection, get_content
from app.utils.route_decorators import login_required
from app.services.users.user_service import user_service
from app.services.orders.order_service import order_service
from app.services.orders.cart_service import cart_service
from app.services.orders.stock_service import stock_service
from app.utils.logging_utils import get_logger
from . import purchase_bp

logger = get_logger(__name__)


@purchase_bp.route('/cart')
def cart_page():
    logger.debug("Mengakses halaman keranjang.")
    return render_template('purchase/cart.html', content=get_content())


@purchase_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    user_id = session.get('user_id')
    user = user_service.get_user_by_id(user_id) if user_id else None
    username = user['username'] if user else "Guest"
    user_log_id = (
        f"ID Pengguna {user_id}"
        if user_id
        else f"ID Sesi {session.get('session_id', 'N/A')}"
    )

    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        logger.info(
            f"session_id baru dibuat untuk checkout: {session['session_id']}"
        )

    session_id = session['session_id']

    if request.method == 'POST':
        logger.info(f"Memproses permintaan POST untuk checkout. {user_log_id}")
        cart_data = None

        if not user_id:
            cart_json = request.form.get('cart_data')

            if not cart_json or cart_json == '{}':
                logger.warning(
                    f"Checkout tamu gagal: Data keranjang kosong. "
                    f"ID Sesi: {session_id}"
                )
                flash("Keranjang Anda kosong.", 'danger')
                return redirect(url_for('purchase.cart_page'))

            try:
                cart_data = json.loads(cart_json)
                logger.debug(f"Data keranjang tamu dimuat: {cart_data}")

            except json.JSONDecodeError:
                logger.error(
                    f"Checkout tamu gagal: JSON cart_data tidak valid. "
                    f"ID Sesi: {session_id}",
                    exc_info=True
                )
                flash("Data keranjang tidak valid.", "danger")
                return redirect(url_for('purchase.cart_page'))

        conn = None

        try:
            if user_id:
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute(
                    '''
                    SELECT id, payment_transaction_id
                    FROM orders
                    WHERE user_id = %s
                    AND status = 'Menunggu Pembayaran'
                    ORDER BY order_date DESC
                    LIMIT 1
                    ''',
                    (user_id,)
                )
                existing_pending_order = cursor.fetchone()
                cursor.close()
                conn.close()
                conn = None

                if existing_pending_order:
                    held_items = stock_service.get_held_items_simple(
                        user_id=user_id,
                        session_id=None
                    )

                    if not held_items:
                        logger.warning(
                            f"Checkout untuk pengguna {user_id}: Penahanan stok kedaluwarsa saat memiliki pesanan tertunda {existing_pending_order['id']}."
                        )
                        flash(
                            "Sesi checkout Anda berakhir karena stok tidak lagi ditahan. Silakan ulangi dari keranjang.",
                            "warning"
                        )
                        return redirect(url_for('purchase.cart_page'))

                    logger.info(
                        f"Pengguna {user_id} memiliki pesanan tertunda {existing_pending_order['id']}. Mengarahkan ke halaman pembayaran."
                    )
                    flash(
                        "Anda memiliki pesanan yang belum dibayar. Silakan selesaikan pembayaran.",
                        "info"
                    )
                    return redirect(
                        url_for(
                            'purchase.payment_page',
                            order_id=existing_pending_order['id']
                        )
                    )
                
                if not user:
                    user = user_service.get_user_by_id(user_id)
                    if not user:
                        logger.error(f"ID Pengguna {user_id} tidak ditemukan selama checkout POST.")
                        flash("Terjadi kesalahan, pengguna tidak ditemukan.", "danger")
                        session.clear()
                        return redirect(url_for('auth.login'))
                    
                shipping_details = {
                    'name': user.get('username'),
                    'phone': user.get('phone'),
                    'address1': user.get('address_line_1'),
                    'address2': user.get('address_line_2', ''),
                    'city': user.get('city'),
                    'province': user.get('province'),
                    'postal_code': user.get('postal_code')
                }

                if not all([
                    shipping_details['phone'],
                    shipping_details['address1'],
                    shipping_details['city'],
                    shipping_details['province'],
                    shipping_details['postal_code']
                ]):
                    logger.warning(
                        f"Checkout gagal untuk pengguna {user_id}: Alamat pengiriman belum lengkap."
                    )
                    flash('Alamat pengiriman belum lengkap. Mohon perbarui di profil Anda.', 'danger')
                    return redirect(url_for('purchase.edit_address'))

                logger.debug(
                    f"Detail pengiriman untuk pengguna {user_id}: {shipping_details}"
                )

            else:
                shipping_details = {
                    'name': request.form['full_name'],
                    'phone': request.form['phone'],
                    'address1': request.form['address_line_1'],
                    'address2': request.form.get('address_line_2', ''),
                    'city': request.form['city'],
                    'province': request.form['province'],
                    'postal_code': request.form['postal_code']
                }

                email_for_order = request.form.get('email')
                if not email_for_order:
                    logger.warning(
                        f"Checkout tamu gagal: Email tidak diisi. ID Sesi: {session_id}"
                    )
                    flash('Email wajib diisi untuk checkout.', 'danger')
                    return redirect(url_for('purchase.checkout'))
                
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT id FROM users WHERE email = %s',
                    (email_for_order,)
                )
                user_exists = cursor.fetchone()
                cursor.close()
                conn.close()
                conn = None

                if user_exists:
                    logger.warning(
                        f"Checkout tamu gagal: Email {email_for_order} sudah terdaftar. ID Sesi: {session_id}"
                    )
                    flash('Email sudah terdaftar. Silakan login untuk melanjutkan.', 'danger')
                    return redirect(
                        url_for(
                            'auth.login',
                            next=url_for('purchase.checkout')
                        )
                    )
                
                session['guest_order_details'] = {
                    'email': email_for_order,
                    **shipping_details
                }
                logger.debug(
                    f"Detail pengiriman untuk tamu {session_id}: {shipping_details}"
                )

            payment_method = request.form['payment_method']
            voucher_code = request.form.get('voucher_code') or None
            try:
                shipping_cost = float(request.form.get('shipping_cost', 0))
            except ValueError:
                logger.warning(f"Nilai shipping_cost tidak valid: {request.form.get('shipping_cost')}. Diubah ke 0.")
                shipping_cost = 0.0


            logger.info(
                f"Membuat pesanan untuk {user_log_id}. "
                f"Metode Pembayaran: {payment_method}, Voucher: {voucher_code}, "
                f"Biaya Pengiriman: {shipping_cost}"
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
                logger.info(
                    f"Pesanan #{order_id} berhasil dibuat untuk {user_log_id}."
                )

                if not user_id:
                    session['guest_order_id'] = order_id

                if payment_method == 'COD':
                    flash(f"Pesanan #{order_id} (COD) berhasil dibuat!", 'success')
                    return redirect(url_for('purchase.order_success'))
                else:
                    logger.info(
                        f"Mengarahkan {user_log_id} ke halaman pembayaran untuk pesanan #{order_id}"
                    )
                    return redirect(
                        url_for(
                            'purchase.payment_page',
                            order_id=order_id
                        )
                    )
                
            else:
                if result.get('message') == 'Terjadi kesalahan internal.':
                     logger.error(
                        f"Pembuatan pesanan gagal untuk {user_log_id} dengan kesalahan internal umum. "
                        f"Periksa log 'order_service' untuk rincian Exception sebelum pesan ini."
                    )
                else:
                    logger.error(
                        f"Pembuatan pesanan gagal untuk {user_log_id}. Alasan spesifik: {result.get('message', 'Kesalahan tidak diketahui dari order_service')}"
                    )
                flash(result.get('message', 'Gagal membuat pesanan.'), 'danger')
                return redirect(url_for('purchase.cart_page'))

        except mysql.connector.Error as db_err:
            logger.error(
                f"Kesalahan database saat checkout POST untuk {user_log_id}: {db_err}",
                exc_info=True
            )
            flash(
                "Terjadi kesalahan database saat memproses checkout.",
                "danger"
            )
            return redirect(url_for('purchase.cart_page'))
        
        except Exception as e:
            logger.error(
                f"Kesalahan tak terduga selama checkout POST untuk {user_log_id}: {e}",
                exc_info=True
            )
            flash("Terjadi kesalahan tak terduga saat checkout.", "danger")
            return redirect(url_for('purchase.cart_page'))
        
        finally:
            if conn and conn.is_connected():
                conn.close()
                logger.debug(f"Koneksi database ditutup untuk checkout POST {user_log_id}.")

    logger.debug(f"Mengakses halaman checkout (GET). {user_log_id}")

    try:
        stock_hold_expires = None
        if user_id:
            cart_details = cart_service.get_cart_details(user_id)

            if not cart_details or not cart_details.get('items'):
                logger.warning(
                    f"Pengguna {user_id} mengakses checkout dengan keranjang kosong."
                )
                flash("Keranjang Anda kosong. Silakan tambahkan item terlebih dahulu.", "warning")
                return redirect(url_for('purchase.cart_page'))
            
            hold_result = stock_service.hold_stock_for_checkout(
                user_id,
                None,
                cart_details['items']
            )

            if not hold_result['success']:
                logger.error(
                    f"Gagal menahan stok untuk pengguna {user_id} saat checkout GET. "
                    f"Alasan: {hold_result['message']}"
                )
                flash(hold_result['message'], 'danger')
                return redirect(url_for('purchase.cart_page'))

            stock_hold_expires = hold_result.get('expires_at')
            logger.info(
                f"Penahanan stok berhasil untuk pengguna {user_id} saat checkout GET. "
                f"Kedaluwarsa pada: {stock_hold_expires}"
            )

        else:
             logger.info(
                f"Menampilkan halaman checkout untuk pengguna tamu. ID Sesi: {session_id}. "
                f"Validasi/penahanan stok akan dilakukan oleh frontend."
            )

        return render_template(
            'purchase/checkout_page.html',
            user=user,
            content=get_content(),
            stock_hold_expires=stock_hold_expires
        )

    except Exception as e:
        logger.error(
            f"Kesalahan memuat halaman checkout (GET) untuk {user_log_id}: {e}",
            exc_info=True
        )
        flash("Gagal memuat halaman checkout.", "danger")
        return redirect(url_for('purchase.cart_page'))


@purchase_bp.route('/checkout/edit_address', methods=['GET', 'POST'])
@login_required
def edit_address():
    user_id = session['user_id']
    logger.debug(f"Pengguna {user_id} mengakses halaman edit alamat.")

    if request.method == 'POST':
        address_data = {
            'phone': request.form.get('phone'),
            'address1': request.form.get('address_line_1'),
            'address2': request.form.get('address_line_2', ''),
            'city': request.form.get('city'),
            'province': request.form.get('province'),
            'postal_code': request.form.get('postal_code')
        }

        logger.info(
            f"Pengguna {user_id} mengirim pembaruan alamat: {address_data}"
        )

        try:
            result = user_service.update_user_address(user_id, address_data)
            if result['success']:
                flash('Alamat berhasil diperbarui.', 'success')
                logger.info(
                    f"Alamat berhasil diperbarui untuk pengguna {user_id}."
                )
                return redirect(url_for('purchase.checkout'))
            else:
                 flash(result.get('message', 'Gagal memperbarui alamat.'), 'danger')
                 logger.warning(f"Gagal memperbarui alamat untuk pengguna {user_id}: {result.get('message')}")
                 return redirect(url_for('purchase.edit_address'))

        except Exception as e:
            logger.error(
                f"Kesalahan saat memperbarui alamat untuk pengguna {user_id} melalui rute checkout: {e}",
                exc_info=True
            )
            flash("Terjadi kesalahan server saat memperbarui alamat.", "danger")
            return redirect(url_for('purchase.edit_address'))

    try:
        user = user_service.get_user_by_id(user_id)
        if not user:
            logger.error(
                f"Pengguna {user_id} tidak ditemukan saat mengakses halaman edit alamat."
            )
            flash("Pengguna tidak ditemukan.", "danger")
            return redirect(url_for('user.user_profile'))

        return render_template(
            'purchase/edit_address_page.html',
            user=user,
            content=get_content()
        )

    except Exception as e:
        logger.error(
            f"Kesalahan memuat halaman edit alamat untuk pengguna {user_id}: {e}",
            exc_info=True
        )
        flash("Gagal memuat halaman edit alamat.", "danger")
        return redirect(url_for('purchase.checkout'))