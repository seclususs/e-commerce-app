import json
import uuid
import random
from datetime import datetime
from db.db_config import get_db_connection
from services.users.user_service import user_service
from services.orders.cart_service import cart_service
from services.orders.stock_service import stock_service
from services.products.variant_service import variant_service
from services.orders.voucher_service import voucher_service

class OrderService:

    def _get_held_items(self, conn, user_id, session_id):
        held_items_query = """
            SELECT p.id as product_id, p.name, sh.quantity, sh.variant_id, pv.size
            FROM stock_holds sh
            JOIN products p ON sh.product_id = p.id
            LEFT JOIN product_variants pv ON sh.variant_id = pv.id
            WHERE
        """
        if user_id:
            held_items_query += "sh.user_id = ?"
            params = (user_id,)
        else:
            held_items_query += "sh.session_id = ?"
            params = (session_id,)

        held_items_query += " AND sh.expires_at > CURRENT_TIMESTAMP"
        return conn.execute(held_items_query, params).fetchall()

    def _prepare_items_for_order(self, conn, held_items):
        if not held_items:
            return None, None, {'success': False, 'message': 'Sesi checkout Anda telah berakhir atau keranjang kosong. Silakan kembali ke keranjang.'}

        product_ids = [item['product_id'] for item in held_items]
        if not product_ids:
             return None, None, {'success': False, 'message': 'Item yang ditahan tidak valid.'}

        placeholders = ', '.join(['?'] * len(product_ids))
        products_db = conn.execute(f'SELECT id, name, price, discount_price FROM products WHERE id IN ({placeholders})', product_ids).fetchall()
        products_map = {p['id']: p for p in products_db}

        subtotal = 0
        items_for_order = []
        for item in held_items:
            product = products_map.get(item['product_id'])
            if not product:
                return None, None, {'success': False, 'message': f"Produk '{item.get('name', 'N/A')}' tidak lagi tersedia."}

            effective_price = product['discount_price'] if product['discount_price'] and product['discount_price'] > 0 else product['price']
            subtotal += effective_price * item['quantity']
            items_for_order.append({
                **product,
                'quantity': item['quantity'],
                'price_at_order': effective_price,
                'variant_id': item['variant_id'],
                'size': item['size']
            })
        return items_for_order, subtotal, None

    def _insert_order_and_items(self, conn, cursor, user_id, subtotal, discount_amount, shipping_cost, final_total, voucher_code, initial_status, payment_method, transaction_id, shipping_details, items_for_order):
        cursor.execute("""
            INSERT INTO orders (user_id, subtotal, discount_amount, shipping_cost, total_amount, voucher_code, status, payment_method, payment_transaction_id,
                                shipping_name, shipping_phone, shipping_address_line_1, shipping_address_line_2,
                                shipping_city, shipping_province, shipping_postal_code)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, subtotal, discount_amount, shipping_cost, final_total, voucher_code.upper() if voucher_code else None, initial_status, payment_method,
              transaction_id, shipping_details['name'], shipping_details['phone'],
              shipping_details['address1'], shipping_details.get('address2', ''),
              shipping_details['city'], shipping_details['province'],
              shipping_details['postal_code']))
        order_id = cursor.lastrowid

        items_data = []
        for item in items_for_order:
            items_data.append((
                order_id, item['id'], item['variant_id'], item['quantity'], item['price_at_order'], item['size']
            ))
        cursor.executemany(
            'INSERT INTO order_items (order_id, product_id, variant_id, quantity, price, size_at_order) VALUES (?, ?, ?, ?, ?, ?)',
            items_data
        )

        # Langsung kurangi stok jika metode pembayaran COD
        if payment_method == 'COD':
            product_ids_with_variants = set()
            for item in items_for_order:
                if item['variant_id']:
                    cursor.execute('UPDATE product_variants SET stock = stock - ? WHERE id = ?', (item['quantity'], item['variant_id']))
                    product_ids_with_variants.add(item['id'])
                else:
                    cursor.execute('UPDATE products SET stock = stock - ? WHERE id = ?', (item['quantity'], item['id']))

            for pid in product_ids_with_variants:
                 variant_service.update_total_stock_from_variants(pid, conn)

        return order_id

    def create_order(self, user_id, session_id, cart_data, shipping_details, payment_method, voucher_code=None, shipping_cost=0):
        conn = get_db_connection()
        try:
            with conn:
                held_items = self._get_held_items(conn, user_id, session_id)
                items_for_order, subtotal, error = self._prepare_items_for_order(conn, held_items)
                if error:
                    return error

                discount_amount = 0
                if voucher_code:
                    voucher_result = voucher_service.validate_and_calculate_voucher(voucher_code, subtotal)
                    if voucher_result['success']:
                        discount_amount = voucher_result['discount_amount']
                    else:
                        return {'success': False, 'message': voucher_result['message']}

                final_total = subtotal - discount_amount + shipping_cost
                initial_status = 'Diproses' if payment_method == 'COD' else 'Menunggu Pembayaran'
                transaction_id = f"TX-{uuid.uuid4().hex[:8].upper()}" if initial_status == 'Menunggu Pembayaran' else None

                cursor = conn.cursor()
                order_id = self._insert_order_and_items(conn, cursor, user_id, subtotal, discount_amount, shipping_cost, final_total, voucher_code, initial_status, payment_method, transaction_id, shipping_details, items_for_order)

                if voucher_code:
                    cursor.execute("UPDATE vouchers SET use_count = use_count + 1 WHERE code = ?", (voucher_code.upper(),))

                if user_id:
                    cursor.execute("DELETE FROM user_carts WHERE user_id = ?", (user_id,))

                stock_service.release_stock_holds(user_id, session_id, conn)

            return {'success': True, 'order_id': order_id}
        except Exception as e:
            print(f"ERROR saat membuat pesanan: {e}")
            return {'success': False, 'message': 'Terjadi kesalahan internal saat memproses pesanan.'}
        finally:
            if conn:
                conn.close()

    def cancel_user_order(self, order_id, user_id):
        conn = get_db_connection()
        try:
            with conn:
                order = conn.execute('SELECT * FROM orders WHERE id = ? AND user_id = ?', (order_id, user_id)).fetchone()
                if not order:
                    return {'success': False, 'message': 'Pesanan tidak ditemukan atau Anda tidak memiliki akses.'}

                if order['status'] not in ['Menunggu Pembayaran', 'Diproses']:
                    return {'success': False, 'message': f'Pesanan tidak dapat dibatalkan karena statusnya "{order["status"]}".'}

                if order['status'] == 'Diproses':
                    self._restock_order_items(order_id, conn)

                conn.execute('UPDATE orders SET status = ? WHERE id = ?', ('Dibatalkan', order_id))

            return {'success': True, 'message': f'Pesanan #{order_id} berhasil dibatalkan.'}
        except Exception as e:
            print(f"ERROR saat membatalkan pesanan: {e}")
            return {'success': False, 'message': 'Terjadi kesalahan internal.'}
        finally:
            conn.close()

    def _restock_order_items(self, order_id, conn):
        """Mengembalikan stok item dari pesanan yang dibatalkan."""
        order_items = conn.execute('SELECT * FROM order_items WHERE order_id = ?', (order_id,)).fetchall()
        product_ids_with_variants = set()
        for item in order_items:
            if item['variant_id']:
                conn.execute('UPDATE product_variants SET stock = stock + ? WHERE id = ?', (item['quantity'], item['variant_id']))
                product_ids_with_variants.add(item['product_id'])
            else:
                conn.execute('UPDATE products SET stock = stock + ? WHERE id = ?', (item['quantity'], item['product_id']))

        for pid in product_ids_with_variants:
            variant_service.update_total_stock_from_variants(pid, conn)

    def update_order_status_and_tracking(self, order_id, new_status, tracking_number_input):
        conn = get_db_connection()
        try:
            with conn:
                order = conn.execute('SELECT status, tracking_number FROM orders WHERE id = ?', (order_id,)).fetchone()
                if not order:
                    return {'success': False, 'message': 'Pesanan tidak ditemukan'}, 404

                original_status = order['status']
                tracking_number = tracking_number_input.strip() if tracking_number_input else order['tracking_number']
                auto_generated_tracking = False

                if new_status == 'Dikirim' and not order['tracking_number'] and not tracking_number:
                    tracking_number = f"HT-{random.randint(10000000, 99999999)}"
                    auto_generated_tracking = True

                if new_status == 'Dibatalkan' and original_status in ['Diproses', 'Dikirim']:
                     self._restock_order_items(order_id, conn)

                conn.execute('UPDATE orders SET status = ?, tracking_number = ? WHERE id = ?', (new_status, tracking_number, order_id))

            message = f'Pesanan #{order_id} berhasil diperbarui!'
            if auto_generated_tracking:
                message += f' Nomor resi otomatis: {tracking_number}'

            status_class_map = {'Menunggu Pembayaran': 'pending', 'Diproses': 'processing', 'Dikirim': 'shipped', 'Selesai': 'completed', 'Dibatalkan': 'cancelled'}

            return {
                'success': True,
                'message': message,
                'data': {
                    'id': order_id,
                    'status': new_status,
                    'status_class': status_class_map.get(new_status, 'pending'),
                    'tracking_number': tracking_number
                }
            }
        except Exception as e:
            print(f"ERROR saat update status pesanan: {e}")
            return {'success': False, 'message': f'Terjadi kesalahan: {e}'}
        finally:
            conn.close()

order_service = OrderService()