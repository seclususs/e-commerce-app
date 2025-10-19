import json
from datetime import datetime
from database.db_config import get_db_connection
from services.user_service import user_service
from services.cart_service import cart_service

class OrderService:
    def validate_and_calculate_voucher(self, code, subtotal):
        """Memvalidasi voucher dan menghitung diskon."""
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

        return {
            'success': True,
            'discount_amount': discount_amount,
            'final_total': final_total,
            'message': 'Voucher berhasil diterapkan!'
        }

    def create_order(self, user_id, cart_data, shipping_details, payment_method, voucher_code=None):
        conn = get_db_connection()
        try:
            with conn:
                if user_id:
                    cart_details = cart_service.get_cart_details(user_id)
                    items_in_cart = cart_details['items']
                    subtotal = cart_details['subtotal']
                    if not items_in_cart:
                        return {'success': False, 'message': 'Keranjang Anda kosong.'}
                else:
                    product_ids = list(cart_data.keys())
                    if not product_ids: return {'success': False, 'message': 'Keranjang Anda kosong.'}
                    placeholders = ', '.join(['?'] * len(product_ids))
                    products_db = conn.execute(f'SELECT id, name, price, discount_price, stock FROM products WHERE id IN ({placeholders})', product_ids).fetchall()
                    products_map = {str(p['id']): p for p in products_db}
                    
                    subtotal = 0
                    items_in_cart = []
                    for pid_str, data in cart_data.items():
                        pid = int(pid_str)
                        qty = data.get('quantity', 0)
                        if pid_str not in products_map:
                             return {'success': False, 'message': f'Produk dengan ID {pid} tidak ditemukan.'}
                        product = products_map[pid_str]
                        effective_price = product['discount_price'] if product['discount_price'] and product['discount_price'] > 0 else product['price']
                        subtotal += effective_price * qty
                        items_in_cart.append({**product, 'quantity': qty, 'price_at_order': effective_price})

                for item in items_in_cart:
                    if item['quantity'] > item['stock']:
                        return {'success': False, 'message': f"Stok untuk '{item['name']}' tidak mencukupi (tersisa {item['stock']})."}
                
                discount_amount = 0
                final_total = subtotal
                if voucher_code:
                    voucher_result = self.validate_and_calculate_voucher(voucher_code, subtotal)
                    if voucher_result['success']:
                        discount_amount = voucher_result['discount_amount']
                        final_total = voucher_result['final_total']
                    else:
                        return {'success': False, 'message': voucher_result['message']}

                initial_status = 'Processing' if payment_method == 'COD' else 'Pending'
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO orders (user_id, subtotal, discount_amount, total_amount, voucher_code, status, payment_method, 
                                        shipping_name, shipping_phone, shipping_address_line_1, shipping_address_line_2,
                                        shipping_city, shipping_province, shipping_postal_code)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, subtotal, discount_amount, final_total, voucher_code.upper() if voucher_code else None, initial_status, payment_method, 
                      shipping_details['name'], shipping_details['phone'], 
                      shipping_details['address1'], shipping_details.get('address2', ''),
                      shipping_details['city'], shipping_details['province'], 
                      shipping_details['postal_code']))
                order_id = cursor.lastrowid

                for item in items_in_cart:
                    price_at_order = item.get('price_at_order')
                    cursor.execute(
                        'INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)',
                        (order_id, item['id'], item['quantity'], price_at_order)
                    )
                    cursor.execute('UPDATE products SET stock = stock - ? WHERE id = ?', (item['quantity'], item['id']))
                
                if voucher_code:
                    cursor.execute("UPDATE vouchers SET use_count = use_count + 1 WHERE code = ?", (voucher_code.upper(),))
                
                if user_id:
                    cursor.execute("DELETE FROM user_carts WHERE user_id = ?", (user_id,))
                
            return {'success': True, 'order_id': order_id}
        except Exception as e:
            print(f"ERROR saat membuat pesanan: {e}")
            return {'success': False, 'message': 'Terjadi kesalahan internal saat memproses pesanan.'}

    def cancel_user_order(self, order_id, user_id):
        conn = get_db_connection()
        try:
            order = conn.execute('SELECT * FROM orders WHERE id = ? AND user_id = ?', (order_id, user_id)).fetchone()
            if not order:
                return {'success': False, 'message': 'Pesanan tidak ditemukan atau Anda tidak memiliki akses.'}
            
            if order['status'] not in ['Pending', 'Processing']:
                return {'success': False, 'message': f'Pesanan tidak dapat dibatalkan karena statusnya "{order["status"]}".'}
            
            order_items = conn.execute('SELECT * FROM order_items WHERE order_id = ?', (order_id,)).fetchall()
            for item in order_items:
                conn.execute('UPDATE products SET stock = stock + ? WHERE id = ?', (item['quantity'], item['product_id']))

            conn.execute('UPDATE orders SET status = ? WHERE id = ?', ('Cancelled', order_id))
            conn.commit()

            return {'success': True, 'message': f'Pesanan #{order_id} berhasil dibatalkan.'}
        except Exception as e:
            conn.rollback()
            print(f"ERROR saat membatalkan pesanan: {e}")
            return {'success': False, 'message': 'Terjadi kesalahan internal.'}
        finally:
            conn.close()

order_service = OrderService()