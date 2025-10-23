import sqlite3
from app.core.db import get_db_connection
from app.services.orders.stock_service import stock_service
from app.services.products.variant_service import variant_service


class PaymentService:

    def process_successful_payment(self, transaction_id):
        conn = get_db_connection()
        try:

            order = conn.execute(
                "SELECT id, status, payment_method FROM orders WHERE payment_transaction_id = ?",
                (transaction_id,)
            ).fetchone()

            if not order:
                 print(f"Webhook: Pesanan dengan transaction_id {transaction_id} tidak ditemukan.")
                 return {'success': False, 'message': 'Pesanan tidak ditemukan.'}

            if order['status'] != 'Menunggu Pembayaran':
                print(f"Webhook: Pesanan #{order['id']} statusnya bukan 'Menunggu Pembayaran' ({order['status']}). Dilewati.")
                return {'success': True, 'message': 'Pesanan sudah diproses sebelumnya atau dibatalkan.'}

            order_id = order['id']
            items = conn.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()

            conn.execute("BEGIN IMMEDIATE")

            
            stock_sufficient = True
            for item in items:
                available_stock = stock_service.get_available_stock(item['product_id'], item['variant_id'], conn)
                if item['quantity'] > available_stock:
                    stock_sufficient = False
                    product_name_info = f"Produk ID {item['product_id']}"
                    if item['variant_id']:
                         variant_info = conn.execute("SELECT size FROM product_variants WHERE id = ?", (item['variant_id'],)).fetchone()
                         if variant_info:
                             product_name_info += f" (Ukuran: {variant_info['size']})"

                    print(f"Webhook Error: Stok tidak cukup untuk pesanan #{order_id}, item {product_name_info}. Diminta: {item['quantity']}, Tersedia: {available_stock}")
                    break

            if not stock_sufficient:
                conn.execute("UPDATE orders SET status = 'Dibatalkan', notes = 'Dibatalkan otomatis karena stok habis saat pembayaran dikonfirmasi.' WHERE id = ?", (order_id,))
                conn.execute(
                     "INSERT INTO order_status_history (order_id, status, notes) VALUES (?, ?, ?)",
                     (order_id, 'Dibatalkan', 'Dibatalkan otomatis karena stok habis saat pembayaran dikonfirmasi.')
                )
                conn.commit()
                return {'success': False, 'message': f"Pembayaran gagal diproses karena stok habis untuk salah satu item pesanan #{order_id}."}

            
            for item in items:
                update_query = "UPDATE {} SET stock = stock - ? WHERE id = ?".format("product_variants" if item['variant_id'] else "products")
                update_id = item['variant_id'] if item['variant_id'] else item['product_id']
                cursor = conn.execute(update_query, (item['quantity'], update_id))
                if cursor.rowcount == 0:
                     raise Exception(f"Gagal mengurangi stok untuk {'variant' if item['variant_id'] else 'product'} ID {update_id}")


            conn.execute("UPDATE orders SET status = 'Diproses' WHERE id = ?", (order_id,))
            conn.execute(
                "INSERT INTO order_status_history (order_id, status, notes) VALUES (?, ?, ?)",
                (order_id, 'Diproses', f'Pembayaran via {order["payment_method"]} berhasil dikonfirmasi.')
            )

            conn.commit()

            
            product_ids_with_variants = {item['product_id'] for item in items if item['variant_id']}
            if product_ids_with_variants:
                
                temp_conn_for_variant = get_db_connection()
                try:
                    for pid in product_ids_with_variants:
                         variant_service.update_total_stock_from_variants(pid)
                finally:
                    temp_conn_for_variant.close()


            print(f"Webhook Success: Pesanan #{order_id} status diubah menjadi Diproses.")
            return {'success': True, 'message': f'Pesanan #{order_id} berhasil diproses.'}

        except sqlite3.OperationalError as e:
            if "locked" in str(e):
                print(f"DATABASE LOCKED error saat memproses webhook untuk transaction_id {transaction_id}: {e}")
                conn.rollback()
                
                return {'success': False, 'message': 'Database terkunci, coba lagi nanti.'}
            else:
                 print(f"OperationalError saat memproses webhook: {e}")
                 conn.rollback()
                 return {'success': False, 'message': 'Kesalahan database saat memproses pembayaran.'}
        except Exception as e:
            conn.rollback()
            print(f"Error processing payment webhook for transaction_id {transaction_id}: {e}")
            return {'success': False, 'message': f'Gagal memproses pembayaran: {e}'}
        finally:
            if conn:
                conn.close()


payment_service = PaymentService()