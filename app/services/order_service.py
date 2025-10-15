import json
from database.db_config import get_db_connection
from services.user_service import user_service

class OrderService:
    """
    Layanan untuk mengelola semua logika bisnis yang terkait dengan pesanan.
    """

    def create_order(self, user_id, cart_data, shipping_details, payment_method, save_address):
        """
        Membuat pesanan baru berdasarkan data keranjang dan informasi pengiriman.
        user_id bisa None untuk guest checkout.
        """
        conn = get_db_connection()
        try:
            product_ids = list(cart_data.keys())
            if not product_ids:
                return {'success': False, 'message': 'Keranjang Anda kosong.'}
                
            placeholders = ', '.join(['?'] * len(product_ids))
            query = f'SELECT id, name, price, stock FROM products WHERE id IN ({placeholders})'
            products_db = conn.execute(query, product_ids).fetchall()
            products_map = {str(p['id']): p for p in products_db}

            for pid, qty in cart_data.items():
                if pid not in products_map:
                    return {'success': False, 'message': f'Produk dengan ID {pid} tidak valid.'}
                if int(qty) > products_map[pid]['stock']:
                    product_name = products_map[pid]['name']
                    stock_left = products_map[pid]['stock']
                    return {'success': False, 'message': f"Stok untuk '{product_name}' tidak mencukupi. Tersisa {stock_left}, Anda meminta {qty}."}

            total_amount = sum(products_map[pid]['price'] * int(qty) for pid, qty in cart_data.items())

            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO orders (user_id, total_amount, status, payment_method, shipping_name, 
                                    shipping_phone, shipping_address_line_1, shipping_address_line_2,
                                    shipping_city, shipping_province, shipping_postal_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, total_amount, 'Pending', payment_method, 
                  shipping_details['name'], shipping_details['phone'], 
                  shipping_details['address1'], shipping_details.get('address2', ''),
                  shipping_details['city'], shipping_details['province'], 
                  shipping_details['postal_code']))
            order_id = cursor.lastrowid

            for pid, qty in cart_data.items():
                price = products_map[pid]['price']
                cursor.execute(
                    'INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)',
                    (order_id, pid, qty, price)
                )
                cursor.execute('UPDATE products SET stock = stock - ? WHERE id = ?', (qty, pid))

            if save_address and user_id:
                user_service.update_user_address(user_id, shipping_details)

            conn.commit()
            return {'success': True, 'order_id': order_id}

        except Exception as e:
            conn.rollback()
            print(f"ERROR saat membuat pesanan: {e}")
            return {'success': False, 'message': 'Terjadi kesalahan internal saat memproses pesanan.'}
        finally:
            conn.close()

    def cancel_user_order(self, order_id, user_id):
        """
        Membatalkan pesanan milik pengguna dan mengembalikan stok.
        """
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