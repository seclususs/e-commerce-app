from datetime import datetime, timedelta
from app.core.db import get_db_connection
import sqlite3

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

            return max(0, product_stock - held_stock)
        except sqlite3.OperationalError as e:
             if "locked" in str(e):
                 print(f"Database locked while getting available stock for product {product_id}, variant {variant_id}. Returning 0.")
                 return 0
             else:
                 raise e
        finally:
            if close_conn:
                conn.commit()
                conn.close()

    def hold_stock_for_checkout(self, user_id, session_id, cart_items):
        conn = get_db_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")

            if user_id:
                conn.execute("DELETE FROM stock_holds WHERE user_id = ?", (user_id,))
            elif session_id:
                conn.execute("DELETE FROM stock_holds WHERE session_id = ?", (session_id,))
            else:
                 conn.rollback()
                 return {'success': False, 'message': 'User ID atau Session ID diperlukan.'}


            for item in cart_items:
                product_id_key = 'id' if 'id' in item else 'product_id'
                variant_id_key = 'variant_id' if 'variant_id' in item else None
                variant_id_value = item.get(variant_id_key)

                available_stock = self.get_available_stock(item[product_id_key], variant_id_value, conn)
                if item['quantity'] > available_stock:
                    size_info = f" (Ukuran: {item.get('size', 'N/A')})" if item.get('size') else ""
                    conn.rollback()
                    return {'success': False, 'message': f"Stok untuk '{item['name']}'{size_info} tidak mencukupi (tersisa {available_stock})."}

            expires_at = datetime.now() + timedelta(minutes=10)
            for item in cart_items:
                product_id_key = 'id' if 'id' in item else 'product_id'
                variant_id_key = 'variant_id' if 'variant_id' in item else None
                variant_id_value = item.get(variant_id_key)
                conn.execute(
                    "INSERT INTO stock_holds (user_id, session_id, product_id, variant_id, quantity, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, session_id, item[product_id_key], variant_id_value, item['quantity'], expires_at)
                )

            conn.commit()
            return {'success': True, 'expires_at': expires_at.isoformat()}
        except sqlite3.OperationalError as e:
             if "locked" in str(e):
                 print(f"Database locked during hold_stock_for_checkout: {e}")
                 conn.rollback()
                 return {'success': False, 'message': 'Sistem sedang sibuk, gagal menahan stok. Coba lagi.'}
             else:
                 print(f"OperationalError holding stock: {e}")
                 conn.rollback()
                 return {'success': False, 'message': 'Terjadi kesalahan database saat validasi stok.'}
        except Exception as e:
            print(f"Error holding stock: {e}")
            conn.rollback()
            return {'success': False, 'message': 'Terjadi kesalahan saat validasi stok.'}
        finally:
            conn.close()

    def release_stock_holds(self, user_id, session_id, conn):
        
        try:
            if user_id:
                conn.execute("DELETE FROM stock_holds WHERE user_id = ?", (user_id,))
            elif session_id:
                conn.execute("DELETE FROM stock_holds WHERE session_id = ?", (session_id,))
        except sqlite3.OperationalError as e:
             if "locked" in str(e):
                 print(f"Database locked while releasing stock holds for user {user_id} / session {session_id}. Might resolve on next attempt.")
                 
             else:
                  raise e
        except Exception as e:
             print(f"Error releasing stock holds: {e}")
             raise e

    def get_held_items_simple(self, user_id, session_id):
        conn = get_db_connection()
        try:
            query = "SELECT product_id, variant_id, quantity FROM stock_holds WHERE "
            params = []
            if user_id:
                query += "user_id = ?"
                params.append(user_id)
            elif session_id:
                query += "session_id = ?"
                params.append(session_id)
            else:
                 return []
            query += " AND expires_at > CURRENT_TIMESTAMP"
            held_items = conn.execute(query, tuple(params)).fetchall()
            return [dict(item) for item in held_items]
        finally:
             conn.close()


stock_service = StockService()