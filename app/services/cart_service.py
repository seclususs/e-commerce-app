from database.db_config import get_db_connection

class CartService:
    def get_cart_details(self, user_id):
        """Mengambil detail item di keranjang untuk user tertentu."""
        conn = get_db_connection()
        try:
            cart_items = conn.execute("""
                SELECT
                    p.id, p.name, p.price, p.discount_price, p.stock, p.image_url,
                    uc.quantity
                FROM user_carts uc
                JOIN products p ON uc.product_id = p.id
                WHERE uc.user_id = ?
            """, (user_id,)).fetchall()

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
            product = conn.execute("SELECT stock, name FROM products WHERE id = ?", (product_id,)).fetchone()
            if not product:
                return {'success': False, 'message': 'Produk tidak ditemukan.'}

            existing_item = conn.execute(
                "SELECT quantity FROM user_carts WHERE user_id = ? AND product_id = ?",
                (user_id, product_id)
            ).fetchone()
            
            current_in_cart = existing_item['quantity'] if existing_item else 0
            total_requested = current_in_cart + quantity

            if total_requested > product['stock']:
                return {'success': False, 'message': f"Stok untuk '{product['name']}' tidak mencukupi (tersisa {product['stock']})."}

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
                stock = conn.execute("SELECT stock FROM products WHERE id = ?", (product_id,)).fetchone()['stock']
                if quantity > stock:
                    return {'success': False, 'message': f'Stok tidak mencukupi. Sisa stok: {stock}.'}
                
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
            for product_id_str, data in local_cart.items():
                product_id = int(product_id_str)
                quantity = data.get('quantity', 0)
                if quantity > 0:
                    product = conn.execute("SELECT stock FROM products WHERE id = ?", (product_id,)).fetchone()
                    if not product: continue

                    existing_item = conn.execute("SELECT quantity FROM user_carts WHERE user_id = ? AND product_id = ?", (user_id, product_id)).fetchone()
                    
                    new_quantity = (existing_item['quantity'] if existing_item else 0) + quantity
                    if new_quantity > product['stock']: new_quantity = product['stock']

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