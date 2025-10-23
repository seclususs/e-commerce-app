from app.core.db import get_db_connection
from app.services.orders.stock_service import stock_service
from app.services.products.variant_service import variant_service


class PaymentService:

    def process_successful_payment(self, transaction_id):
        conn = get_db_connection()
        try:
            with conn:
                order = conn.execute("SELECT * FROM orders WHERE payment_transaction_id = ? AND status = 'Menunggu Pembayaran'", (transaction_id,)).fetchone()
                if not order:
                    return {'success': False, 'message': 'Pesanan tidak ditemukan atau sudah diproses.'}

                order_id = order['id']
                items = conn.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()

                for item in items:
                    available_stock = stock_service.get_available_stock(item['product_id'], item['variant_id'], conn)
                    if item['quantity'] > available_stock:
                        conn.execute("UPDATE orders SET status = 'Dibatalkan' WHERE id = ?", (order_id,))
                        return {'success': False, 'message': f"Pembayaran gagal diproses karena stok habis untuk produk ID {item['product_id']}."}

                for item in items:
                    update_query = "UPDATE {} SET stock = stock - ? WHERE id = ?".format("product_variants" if item['variant_id'] else "products")
                    update_id = item['variant_id'] if item['variant_id'] else item['product_id']
                    conn.execute(update_query, (item['quantity'], update_id))

                conn.execute("UPDATE orders SET status = 'Diproses' WHERE id = ?", (order_id,))

                product_ids_with_variants = {item['product_id'] for item in items if item['variant_id']}
                for pid in product_ids_with_variants:
                    variant_service.update_total_stock_from_variants(pid)

            return {'success': True, 'message': f'Pesanan #{order_id} berhasil diproses.'}
        except Exception as e:
            print(f"Error processing payment: {e}")
            return {'success': False, 'message': 'Gagal memproses pembayaran.'}


payment_service = PaymentService()