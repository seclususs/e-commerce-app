import json
import uuid
import random
from datetime import datetime
import mysql.connector
from app.core.db import get_db_connection
from app.services.users.user_service import user_service
from app.services.orders.cart_service import cart_service
from app.services.orders.stock_service import stock_service
from app.services.products.variant_service import variant_service
from app.services.orders.voucher_service import voucher_service
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class OrderService:


    def _get_held_items(self, conn, user_id, session_id):
        log_id = f"User {user_id}" if user_id else f"Session {session_id}"
        logger.debug(f"Mengambil item yang ditahan untuk {log_id}")
        cursor = conn.cursor(dictionary=True)

        held_items_query = """
            SELECT p.id AS product_id, p.name, sh.quantity, sh.variant_id, pv.size
            FROM stock_holds sh
            JOIN products p ON sh.product_id = p.id
            LEFT JOIN product_variants pv ON sh.variant_id = pv.id
            WHERE
        """

        params = []

        if user_id:
            held_items_query += "sh.user_id = %s"
            params.append(user_id)
        elif session_id:
            held_items_query += "sh.session_id = %s"
            params.append(session_id)
        else:
            logger.error("Mencoba mengambil item yang ditahan tanpa user_id atau session_id.")
            cursor.close()
            return []

        held_items_query += " AND sh.expires_at > CURRENT_TIMESTAMP"
        cursor.execute(held_items_query, tuple(params))
        result = cursor.fetchall()
        cursor.close()

        logger.info(f"Menemukan {len(result)} item yang ditahan untuk {log_id}")
        return result


    def _prepare_items_for_order(self, conn, held_items):
        if not held_items:
            logger.warning("Persiapan item gagal: Tidak ada item yang ditahan atau item telah kedaluwarsa.")
            return None, None, {
                'success': False,
                'message': 'Sesi checkout Anda telah berakhir atau keranjang kosong. Silakan kembali ke keranjang.'
            }

        product_ids = [item['product_id'] for item in held_items]
        logger.debug(f"Mempersiapkan item untuk pesanan. ID Produk: {product_ids}")

        if not product_ids:
            logger.error("Persiapan item gagal: Daftar item yang ditahan kosong.")
            return None, None, {'success': False, 'message': 'Item yang ditahan tidak valid.'}

        cursor = conn.cursor(dictionary=True)
        placeholders = ', '.join(['%s'] * len(product_ids))
        cursor.execute(
            f"SELECT id, name, price, discount_price FROM products WHERE id IN ({placeholders})",
            tuple(product_ids)
        )
        products_db = cursor.fetchall()
        cursor.close()

        products_map = {p['id']: p for p in products_db}
        subtotal = 0
        items_for_order = []

        for item in held_items:
            product = products_map.get(item['product_id'])
            if not product:
                logger.error(
                    f"Persiapan item gagal: ID Produk {item['product_id']} (Nama: {item.get('name', 'N/A')}) tidak ditemukan."
                )
                return None, None, {
                    'success': False,
                    'message': f"Produk '{item.get('name', 'N/A')}' tidak lagi tersedia."
                }

            effective_price = (
                product['discount_price']
                if product['discount_price'] and product['discount_price'] > 0
                else product['price']
            )

            subtotal += effective_price * item['quantity']

            items_for_order.append({
                **product,
                'quantity': item['quantity'],
                'price_at_order': effective_price,
                'variant_id': item['variant_id'],
                'size': item['size']
            })

        logger.info(f"Mempersiapkan {len(items_for_order)} item untuk pesanan. Subtotal: {subtotal}")
        return items_for_order, subtotal, None


    def _insert_order_and_items(
        self, conn, user_id, subtotal, discount_amount, shipping_cost,
        final_total, voucher_code, initial_status, payment_method,
        transaction_id, shipping_details, items_for_order
    ):
        cursor = conn.cursor()
        order_id = None

        try:
            log_id = f"User {user_id}" if user_id else "Guest"
            logger.debug(
                f"Memasukkan catatan pesanan untuk {log_id}. "
                f"Total: {final_total}, Metode: {payment_method}, Status: {initial_status}"
            )

            cursor.execute(
                """
                INSERT INTO orders (
                    user_id, subtotal, discount_amount, shipping_cost, total_amount,
                    voucher_code, status, payment_method, payment_transaction_id,
                    shipping_name, shipping_phone, shipping_address_line_1,
                    shipping_address_line_2, shipping_city, shipping_province,
                    shipping_postal_code
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id, subtotal, discount_amount, shipping_cost, final_total,
                    voucher_code.upper() if voucher_code else None, 'Pesanan Dibuat',
                    payment_method, transaction_id, shipping_details['name'],
                    shipping_details['phone'], shipping_details['address1'],
                    shipping_details.get('address2', ''), shipping_details['city'],
                    shipping_details['province'], shipping_details['postal_code']
                )
            )

            order_id = cursor.lastrowid

            cursor.execute(
                "INSERT INTO order_status_history (order_id, status, notes) VALUES (%s, %s, %s)",
                (order_id, 'Pesanan Dibuat', 'Pesanan berhasil dibuat oleh pelanggan.')
            )

            items_data = [
                (
                    order_id, item['id'], item['variant_id'], item['quantity'],
                    item['price_at_order'], item['size']
                )
                for item in items_for_order
            ]

            cursor.executemany(
                """
                INSERT INTO order_items (
                    order_id, product_id, variant_id, quantity, price, size_at_order
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                items_data
            )

            logger.debug(f"Memasukkan {len(items_data)} item pesanan untuk ID Pesanan {order_id}")

            if initial_status != 'Pesanan Dibuat':
                cursor.execute(
                    "UPDATE orders SET status = %s WHERE id = %s",
                    (initial_status, order_id)
                )
                notes = (
                    'Pembayaran COD dipilih.'
                    if payment_method == 'COD'
                    else f"Menunggu pembayaran via {payment_method}"
                )
                cursor.execute(
                    "INSERT INTO order_status_history (order_id, status, notes) VALUES (%s, %s, %s)",
                    (order_id, initial_status, notes)
                )

            if payment_method == 'COD':
                self._deduct_stock_for_cod_order(conn, order_id, items_for_order)

            cursor.close()
            return order_id

        except Exception as e:
            logger.error(
                f"Kesalahan saat penyisipan pesanan untuk ID Pesanan {order_id or 'baru'}: {e}",
                exc_info=True
            )
            cursor.close()
            raise


    def _deduct_stock_for_cod_order(self, conn, order_id, items_for_order):
        cursor = conn.cursor()
        product_ids_with_variants = set()

        for item in items_for_order:
            if item['variant_id']:
                cursor.execute(
                    "UPDATE product_variants SET stock = stock - %s WHERE id = %s",
                    (item['quantity'], item['variant_id'])
                )
                product_ids_with_variants.add(item['id'])
            else:
                cursor.execute(
                    "UPDATE products SET stock = stock - %s WHERE id = %s",
                    (item['quantity'], item['id'])
                )

        cursor.close()
        self._update_total_stock_after_variant_updates(conn, product_ids_with_variants)


    def _update_total_stock_after_variant_updates(self, conn, product_ids):
        cursor = conn.cursor(dictionary=True)

        for product_id in product_ids:
            cursor.execute(
                "SELECT SUM(stock) AS total FROM product_variants WHERE product_id = %s",
                (product_id,)
            )
            total_stock_row = cursor.fetchone()
            total_stock = total_stock_row['total'] if total_stock_row else 0

            cursor.execute(
                "UPDATE products SET stock = %s WHERE id = %s",
                (total_stock, product_id)
            )

        cursor.close()


    def create_order(
        self, user_id, session_id, cart_data, shipping_details,
        payment_method, voucher_code=None, shipping_cost=0
    ):
        log_id = f"User {user_id}" if user_id else f"Session {session_id}"
        logger.info(
            f"Pembuatan pesanan dimulai untuk {log_id}. "
            f"Metode: {payment_method}, Voucher: {voucher_code}, Pengiriman: {shipping_cost}"
        )

        conn = get_db_connection()
        order_id = None

        try:
            conn.start_transaction()

            held_items = self._get_held_items(conn, user_id, session_id)
            items_for_order, subtotal, error = self._prepare_items_for_order(conn, held_items)

            if error:
                conn.rollback()
                return error

            discount_amount = 0

            if voucher_code:
                voucher_result = voucher_service.validate_and_calculate_voucher(
                    voucher_code, subtotal
                )
                if voucher_result['success']:
                    discount_amount = voucher_result['discount_amount']
                else:
                    conn.rollback()
                    return {'success': False, 'message': voucher_result['message']}

            final_total = subtotal - discount_amount + shipping_cost
            initial_status = 'Diproses' if payment_method == 'COD' else 'Menunggu Pembayaran'
            transaction_id = f"TX-{uuid.uuid4().hex[:8].upper()}" if initial_status == 'Menunggu Pembayaran' else None

            order_id = self._insert_order_and_items(
                conn, user_id, subtotal, discount_amount, shipping_cost, final_total,
                voucher_code, initial_status, payment_method, transaction_id,
                shipping_details, items_for_order
            )

            self._post_order_cart_cleanup(conn, user_id, voucher_code)

            stock_service.release_stock_holds(user_id, session_id, conn)
            conn.commit()

            return {'success': True, 'order_id': order_id}

        except mysql.connector.Error:
            conn.rollback()
            return {'success': False, 'message': 'Terjadi kesalahan database.'}

        except Exception:
            conn.rollback()
            return {'success': False, 'message': 'Terjadi kesalahan internal.'}

        finally:
            if conn.is_connected():
                conn.close()


    def _post_order_cart_cleanup(self, conn, user_id, voucher_code):
        cursor = conn.cursor()

        if voucher_code:
            cursor.execute(
                "UPDATE vouchers SET use_count = use_count + 1 WHERE code = %s",
                (voucher_code.upper(),)
            )

        if user_id:
            cursor.execute(
                "DELETE FROM user_carts WHERE user_id = %s",
                (user_id,)
            )

        cursor.close()


    def cancel_user_order(self, order_id, user_id):
        logger.info(f"Pengguna {user_id} mencoba membatalkan pesanan {order_id}")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            conn.start_transaction()
            cursor.execute(
                "SELECT * FROM orders WHERE id = %s AND user_id = %s",
                (order_id, user_id)
            )
            order = cursor.fetchone()

            if not order:
                return {'success': False, 'message': 'Pesanan tidak ditemukan.'}

            current_status = order['status']

            if current_status not in ['Menunggu Pembayaran', 'Diproses']:
                return {
                    'success': False,
                    'message': f'Pesanan tidak dapat dibatalkan karena statusnya "{current_status}".'
                }

            if current_status == 'Diproses':
                self._restock_order_items(order_id, conn)

            cursor.execute(
                "UPDATE orders SET status = %s WHERE id = %s",
                ('Dibatalkan', order_id)
            )
            cursor.execute(
                "INSERT INTO order_status_history (order_id, status, notes) VALUES (%s, %s, %s)",
                (order_id, 'Dibatalkan', 'Pesanan dibatalkan oleh pelanggan.')
            )

            conn.commit()

            return {'success': True, 'message': f'Pesanan #{order_id} dibatalkan.'}

        except Exception:
            conn.rollback()
            return {'success': False, 'message': 'Gagal membatalkan pesanan.'}

        finally:
            cursor.close()
            conn.close()


    def _restock_order_items(self, order_id, conn):
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM order_items WHERE order_id = %s', (order_id,))
        order_items = cursor.fetchall()
        cursor.close()

        if not order_items:
            logger.warning(f"Tidak ada item yang ditemukan untuk restock pada pesanan {order_id}")
            return

        cursor = conn.cursor()
        product_ids_with_variants = set()

        for item in order_items:
            if item['variant_id']:
                cursor.execute(
                    "UPDATE product_variants SET stock = stock + %s WHERE id = %s",
                    (item['quantity'], item['variant_id'])
                )
                product_ids_with_variants.add(item['product_id'])
            else:
                cursor.execute(
                    "UPDATE products SET stock = stock + %s WHERE id = %s",
                    (item['quantity'], item['product_id'])
                )

        cursor.close()

        for product_id in product_ids_with_variants:
            variant_service.update_total_stock_from_variants(product_id)


    def update_order_status_and_tracking(self, order_id, new_status, tracking_number_input):
        logger.info(
            f"Admin memperbarui pesanan {order_id}: "
            f"Status: {new_status}, Resi: {tracking_number_input}"
        )

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            conn.start_transaction()

            cursor.execute(
                "SELECT status, tracking_number FROM orders WHERE id = %s",
                (order_id,)
            )
            order = cursor.fetchone()

            if not order:
                return {'success': False, 'message': 'Pesanan tidak ditemukan'}, 404

            original_status = order['status']
            tracking_number = tracking_number_input.strip() if tracking_number_input else order['tracking_number']

            status_changed = original_status != new_status
            tracking_changed = (order['tracking_number'] != tracking_number)

            if new_status == 'Dibatalkan':
                if original_status in ['Diproses', 'Dikirim']:
                    self._restock_order_items(order_id, conn)
                elif original_status == 'Dibatalkan':
                    conn.rollback()
                    return {'success': False, 'message': 'Tidak dapat mengubah status dari Dibatalkan.'}

            if not status_changed and not tracking_changed:
                return {
                    'success': True,
                    'message': 'Tidak ada perubahan pada data pesanan.',
                    'data': {
                        'id': order_id,
                        'status': original_status,
                        'status_class': original_status.lower().replace(' ', '-'),
                        'tracking_number': order['tracking_number']
                    }
                }

            cursor.execute(
                "UPDATE orders SET status = %s, tracking_number = %s WHERE id = %s",
                (new_status, tracking_number, order_id)
            )
            notes = f'Status diubah dari "{original_status}" menjadi "{new_status}".'

            if tracking_changed:
                notes += f" Nomor resi: {tracking_number}"

            cursor.execute(
                "INSERT INTO order_status_history (order_id, status, notes) VALUES (%s, %s, %s)",
                (order_id, new_status, notes)
            )

            conn.commit()

            return {
                'success': True,
                'message': f'Pesanan #{order_id} berhasil diperbarui',
                'data': {
                    'id': order_id,
                    'status': new_status,
                    'status_class': new_status.lower().replace(' ', '-'),
                    'tracking_number': tracking_number
                }
            }

        except Exception:
            conn.rollback()
            return {'success': False, 'message': 'Gagal memperbarui status pesanan'}

        finally:
            cursor.close()
            conn.close()


order_service = OrderService()