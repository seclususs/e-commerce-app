from datetime import datetime, timedelta
from app.core.db import get_db_connection


class StockService:

    def get_available_stock(self, product_id, variant_id=None, conn=None):
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True

        try:
            conn.execute("DELETE FROM stock_holds WHERE expires_at < CURRENT_TIMESTAMP")
            if not close_conn:
                conn.commit()

            base_stock_query = "SELECT stock FROM {} WHERE id = ?".format(
                "product_variants" if variant_id else "products"
            )
            stock_id = variant_id if variant_id else product_id

            product_stock_row = conn.execute(base_stock_query, (stock_id,)).fetchone()
            if not product_stock_row:
                return 0

            product_stock = product_stock_row['stock']

            held_stock_query = "SELECT SUM(quantity) as held FROM stock_holds WHERE product_id = ?"
            params = [product_id]
            if variant_id:
                held_stock_query += " AND variant_id = ?"
                params.append(variant_id)
            else:
                held_stock_query += " AND variant_id IS NULL"

            held_stock_row = conn.execute(held_stock_query, tuple(params)).fetchone()

            held_stock = held_stock_row['held'] if held_stock_row and held_stock_row['held'] else 0

            return product_stock - held_stock
        finally:
            if close_conn:
                conn.commit()
                conn.close()

    def hold_stock_for_checkout(self, user_id, session_id, cart_items):
        conn = get_db_connection()
        try:
            with conn:
                if user_id:
                    conn.execute("DELETE FROM stock_holds WHERE user_id = ?", (user_id,))
                else:
                    conn.execute("DELETE FROM stock_holds WHERE session_id = ?", (session_id,))

                for item in cart_items:
                    product_id_key = 'id' if 'id' in item else 'product_id'
                    variant_id_key = 'variant_id' if 'variant_id' in item else None

                    available_stock = self.get_available_stock(item[product_id_key], item.get(variant_id_key), conn)
                    if item['quantity'] > available_stock:
                        size_info = f" (Ukuran: {item.get('size', 'N/A')})" if item.get('size') else ""
                        return {'success': False, 'message': f"Stok untuk '{item['name']}'{size_info} tidak mencukupi (tersisa {available_stock})."}

                expires_at = datetime.now() + timedelta(minutes=10)
                for item in cart_items:
                    product_id_key = 'id' if 'id' in item else 'product_id'
                    variant_id_key = 'variant_id' if 'variant_id' in item else None
                    conn.execute(
                        "INSERT INTO stock_holds (user_id, session_id, product_id, variant_id, quantity, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (user_id, session_id, item[product_id_key], item.get(variant_id_key), item['quantity'], expires_at)
                    )
            return {'success': True, 'expires_at': expires_at.isoformat()}
        except Exception as e:
            print(f"Error holding stock: {e}")
            return {'success': False, 'message': 'Terjadi kesalahan saat validasi stok.'}
        finally:
            conn.close()

    def release_stock_holds(self, user_id, session_id, conn):
        if user_id:
            conn.execute("DELETE FROM stock_holds WHERE user_id = ?", (user_id,))
        elif session_id:
            conn.execute("DELETE FROM stock_holds WHERE session_id = ?", (session_id,))


stock_service = StockService()