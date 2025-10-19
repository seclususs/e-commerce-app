import json
from database.db_config import get_db_connection

class CartService:
    def get_cart_details(self, user_id, session_id=None):
        """
        Mengambil detail item di keranjang untuk user atau session tertentu.
        Memprioritaskan user_id jika ada.
        """
        conn = get_db_connection()
        try:
            if user_id:
                cart_items = conn.execute("""
                    SELECT
                        p.id, p.name, p.price, p.discount_price, p.stock, p.image_url,
                        uc.quantity
                    FROM user_carts uc
                    JOIN products p ON uc.product_id = p.id
                    WHERE uc.user_id = ?
                """, (user_id,)).fetchall()
            elif session_id:
                # Untuk tamu, kita asumsikan data keranjang ada di frontend (localStorage)
                # Fungsi ini akan dipanggil dari checkout dengan data keranjang eksplisit
                # Jadi, jika hanya session_id, kita kembalikan keranjang kosong
                return {'items': [], 'subtotal': 0}
            else:
                 return {'items': [], 'subtotal': 0}


            subtotal = 0
            items = []
            for item in cart_items:
                item_dict = dict(item)
                effective_price = item_dict['discount_price'] if item_dict['discount_price'] and item_dict['discount_price'] > 0 else item_dict['price']
                item_dict['line_total'] = effective_price * item_dict['quantity']
                subtotal += item_dict['line_total']
                items.append(item_dict)

            return {'items': items, 'subtotal': subtotal}
        finally:
            conn.close()

    def add_to_cart(self, user_id, product_id, quantity):
        """Menambah atau mengupdate item di keranjang database."""
        conn = get_db_connection()
        try:
            from services.product_service import product_service
            available_stock = product_service.get_available_stock(product_id, conn)
            product_name = conn.execute("SELECT name FROM products WHERE id = ?", (product_id,)).fetchone()['name']

            existing_item = conn.execute(
                "SELECT quantity FROM user_carts WHERE user_id = ? AND product_id = ?",
                (user_id, product_id)
            ).fetchone()
            
            current_in_cart = existing_item['quantity'] if existing_item else 0
            total_requested = current_in_cart + quantity

            if total_requested > available_stock:
                return {'success': False, 'message': f"Stok untuk '{product_name}' tidak mencukupi (tersisa {available_stock})."}

            if existing_item:
                conn.execute(
                    "UPDATE user_carts SET quantity = ? WHERE user_id = ? AND product_id = ?",
                    (total_requested, user_id, product_id)
                )
            else:
                conn.execute(
                    "INSERT INTO user_carts (user_id, product_id, quantity) VALUES (?, ?, ?)",
                    (user_id, product_id, quantity)
                )
            conn.commit()
            return {'success': True, 'message': 'Item ditambahkan ke keranjang.'}
        finally:
            conn.close()

    def update_cart_item(self, user_id, product_id, quantity):
        """Mengupdate kuantitas item atau menghapusnya jika kuantitas <= 0."""
        conn = get_db_connection()
        try:
            if quantity <= 0:
                conn.execute("DELETE FROM user_carts WHERE user_id = ? AND product_id = ?", (user_id, product_id))
            else:
                from services.product_service import product_service
                available_stock = product_service.get_available_stock(product_id, conn)

                if quantity > available_stock:
                    return {'success': False, 'message': f'Stok tidak mencukupi. Sisa stok tersedia: {available_stock}.'}
                
                conn.execute(
                    "UPDATE user_carts SET quantity = ? WHERE user_id = ? AND product_id = ?",
                    (quantity, user_id, product_id)
                )
            conn.commit()
            return {'success': True}
        finally:
            conn.close()

    def merge_local_cart_to_db(self, user_id, local_cart):
        """Menggabungkan keranjang dari localStorage ke database saat login."""
        if not isinstance(local_cart, dict):
            return {'success': False, 'message': 'Format keranjang lokal tidak valid.'}
        
        conn = get_db_connection()
        try:
            from services.product_service import product_service
            for product_id_str, data in local_cart.items():
                product_id = int(product_id_str)
                quantity = data.get('quantity', 0)
                if quantity > 0:
                    available_stock = product_service.get_available_stock(product_id, conn)
                    if available_stock <= 0: continue

                    existing_item = conn.execute("SELECT quantity FROM user_carts WHERE user_id = ? AND product_id = ?", (user_id, product_id)).fetchone()
                    
                    new_quantity = (existing_item['quantity'] if existing_item else 0) + quantity
                    if new_quantity > available_stock: new_quantity = available_stock

                    if existing_item:
                        conn.execute("UPDATE user_carts SET quantity = ? WHERE user_id = ? AND product_id = ?", (new_quantity, user_id, product_id))
                    else:
                        conn.execute("INSERT INTO user_carts (user_id, product_id, quantity) VALUES (?, ?, ?)", (user_id, product_id, new_quantity))

            conn.commit()
            return {'success': True, 'message': 'Keranjang berhasil disinkronkan.'}
        except Exception as e:
            conn.rollback()
            print(f"Error merging cart: {e}")
            return {'success': False, 'message': 'Gagal menyinkronkan keranjang.'}
        finally:
            conn.close()

cart_service = CartService()