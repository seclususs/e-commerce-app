import json
import uuid
from datetime import datetime
from db.db_config import get_db_connection
from services.users.user_service import user_service
from services.orders.cart_service import cart_service
from services.orders.stock_service import stock_service
from services.products.variant_service import variant_service

class OrderService:
    
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

    def create_order(self, user_id, session_id, cart_data, shipping_details, payment_method, voucher_code=None, shipping_cost=0):
        conn = get_db_connection()
        try:
            with conn:
                # Dapatkan item yang ditahan dari stock_service
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
                
                held_items = conn.execute(held_items_query, params).fetchall()

                if not held_items:
                    return {'success': False, 'message': 'Sesi checkout Anda telah berakhir. Silakan kembali ke keranjang.'}

                product_ids = [item['product_id'] for item in held_items]
                placeholders = ', '.join(['?'] * len(product_ids))
                products_db = conn.execute(f'SELECT id, name, price, discount_price FROM products WHERE id IN ({placeholders})', product_ids).fetchall()
                products_map = {p['id']: p for p in products_db}

                subtotal = 0
                items_for_order = []
                for item in held_items:
                    product = products_map.get(item['product_id'])
                    if not product: continue
                    
                    # Verifikasi stok sekali lagi sebelum membuat pesanan
                    available_stock = stock_service.get_available_stock(item['product_id'], item['variant_id'], conn)
                    if item['quantity'] > available_stock:
                         size_info = f" (Ukuran: {item['size']})" if item.get('size') else ""
                         return {'success': False, 'message': f"Stok untuk '{product['name']}'{size_info} telah habis saat akan memproses pesanan."}

                    effective_price = product['discount_price'] if product['discount_price'] and product['discount_price'] > 0 else product['price']
                    subtotal += effective_price * item['quantity']
                    items_for_order.append({
                        **product, 
                        'quantity': item['quantity'], 
                        'price_at_order': effective_price,
                        'variant_id': item['variant_id'],
                        'size': item['size']
                    })
                
                discount_amount = 0
                if voucher_code:
                    voucher_result = self.validate_and_calculate_voucher(voucher_code, subtotal)
                    if voucher_result['success']:
                        discount_amount = voucher_result['discount_amount']
                    else:
                        return {'success': False, 'message': voucher_result['message']}

                final_total = subtotal - discount_amount + shipping_cost
                initial_status = 'Diproses' if payment_method == 'COD' else 'Menunggu Pembayaran'
                transaction_id = f"TX-{uuid.uuid4().hex[:8].upper()}" if initial_status == 'Menunggu Pembayaran' else None

                cursor = conn.cursor()
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

                for item in items_for_order:
                    cursor.execute(
                        'INSERT INTO order_items (order_id, product_id, variant_id, quantity, price, size_at_order) VALUES (?, ?, ?, ?, ?, ?)',
                        (order_id, item['id'], item['variant_id'], item['quantity'], item['price_at_order'], item['size'])
                    )
                    # Hanya kurangi stok jika pembayaran langsung (COD)
                    if payment_method == 'COD':
                        if item['variant_id']:
                            cursor.execute('UPDATE product_variants SET stock = stock - ? WHERE id = ?', (item['quantity'], item['variant_id']))
                        else:
                            cursor.execute('UPDATE products SET stock = stock - ? WHERE id = ?', (item['quantity'], item['id']))
                
                if voucher_code:
                    cursor.execute("UPDATE vouchers SET use_count = use_count + 1 WHERE code = ?", (voucher_code.upper(),))
                
                if user_id:
                    cursor.execute("DELETE FROM user_carts WHERE user_id = ?", (user_id,))
                
                # Lepaskan hold setelah pesanan dibuat
                stock_service.release_stock_holds(user_id, session_id, conn)

                # Update stok total pada produk utama jika ada varian
                product_ids_with_variants = {item['id'] for item in items_for_order if item['variant_id']}
                for pid in product_ids_with_variants:
                    variant_service.update_total_stock_from_variants(pid)

            return {'success': True, 'order_id': order_id}
        except Exception as e:
            print(f"ERROR saat membuat pesanan: {e}")
            return {'success': False, 'message': 'Terjadi kesalahan internal saat memproses pesanan.'}

    def process_successful_payment(self, transaction_id):
        conn = get_db_connection()
        try:
            with conn:
                order = conn.execute("SELECT * FROM orders WHERE payment_transaction_id = ? AND status = 'Menunggu Pembayaran'", (transaction_id,)).fetchone()
                if not order:
                    return {'success': False, 'message': 'Pesanan tidak ditemukan atau sudah diproses.'}
                
                order_id = order['id']
                items = conn.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
                
                # Cek stok sebelum mengurangi
                for item in items:
                    available_stock = stock_service.get_available_stock(item['product_id'], item['variant_id'], conn)
                    if item['quantity'] > available_stock:
                        conn.execute("UPDATE orders SET status = 'Dibatalkan' WHERE id = ?", (order_id,))
                        # TODO: Logika untuk refund jika diperlukan
                        return {'success': False, 'message': f"Pembayaran gagal diproses karena stok habis untuk produk ID {item['product_id']}."}

                # Kurangi stok
                for item in items:
                    update_query = "UPDATE {} SET stock = stock - ? WHERE id = ?".format("product_variants" if item['variant_id'] else "products")
                    update_id = item['variant_id'] if item['variant_id'] else item['product_id']
                    conn.execute(update_query, (item['quantity'], update_id))
                
                conn.execute("UPDATE orders SET status = 'Diproses' WHERE id = ?", (order_id,))
                
                # Update stok total pada produk utama
                product_ids_with_variants = {item['product_id'] for item in items if item['variant_id']}
                for pid in product_ids_with_variants:
                    variant_service.update_total_stock_from_variants(pid)

            return {'success': True, 'message': f'Pesanan #{order_id} berhasil diproses.'}
        except Exception as e:
            print(f"Error processing payment: {e}")
            return {'success': False, 'message': 'Gagal memproses pembayaran.'}


    def cancel_user_order(self, order_id, user_id):
        conn = get_db_connection()
        try:
            with conn:
                order = conn.execute('SELECT * FROM orders WHERE id = ? AND user_id = ?', (order_id, user_id)).fetchone()
                if not order:
                    return {'success': False, 'message': 'Pesanan tidak ditemukan atau Anda tidak memiliki akses.'}
                
                if order['status'] not in ['Menunggu Pembayaran', 'Diproses']:
                    return {'success': False, 'message': f'Pesanan tidak dapat dibatalkan karena statusnya "{order["status"]}".'}
                
                # Kembalikan stok HANYA jika pesanan sudah mengurangi stok (status 'Diproses' atau status lain yang relevan)
                if order['status'] == 'Diproses':
                    order_items = conn.execute('SELECT * FROM order_items WHERE order_id = ?', (order_id,)).fetchall()
                    for item in order_items:
                        update_query = "UPDATE {} SET stock = stock + ? WHERE id = ?".format("product_variants" if item['variant_id'] else "products")
                        update_id = item['variant_id'] if item['variant_id'] else item['product_id']
                        conn.execute(update_query, (item['quantity'], update_id))
                    
                    product_ids_with_variants = {item['product_id'] for item in order_items if item['variant_id']}
                    for pid in product_ids_with_variants:
                        variant_service.update_total_stock_from_variants(pid)

                conn.execute('UPDATE orders SET status = ? WHERE id = ?', ('Dibatalkan', order_id))

            return {'success': True, 'message': f'Pesanan #{order_id} berhasil dibatalkan.'}
        except Exception as e:
            print(f"ERROR saat membatalkan pesanan: {e}")
            return {'success': False, 'message': 'Terjadi kesalahan internal.'}
        finally:
            conn.close()

order_service = OrderService()