import json
from database.db_config import get_db_connection

class CartService:
    
    def get_cart_details(self, user_id):
        conn = get_db_connection()
        try:
            # Query utama untuk mengambil item, termasuk yang tidak punya varian
            query = """
                SELECT
                    p.id, p.name, p.price, p.discount_price, p.image_url, p.has_variants,
                    uc.quantity, uc.variant_id,
                    pv.size,
                    CASE
                        WHEN uc.variant_id IS NOT NULL THEN pv.stock
                        ELSE p.stock
                    END as stock
                FROM user_carts uc
                JOIN products p ON uc.product_id = p.id
                LEFT JOIN product_variants pv ON uc.variant_id = pv.id
                WHERE uc.user_id = ?
            """
            cart_items = conn.execute(query, (user_id,)).fetchall()

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

    def add_to_cart(self, user_id, product_id, quantity, variant_id=None):
        conn = get_db_connection()
        try:
            from services.product_service import product_service
            product = conn.execute("SELECT name, has_variants FROM products WHERE id = ?", (product_id,)).fetchone()
            if not product:
                return {'success': False, 'message': 'Produk tidak ditemukan.'}
            
            if product['has_variants'] and not variant_id:
                return {'success': False, 'message': 'Silakan pilih ukuran untuk produk ini.'}

            available_stock = product_service.get_available_stock(product_id, variant_id, conn)
            
            # Tentukan klausa WHERE berdasarkan adanya variant_id
            where_clause = "user_id = ? AND product_id = ? AND variant_id = ?" if variant_id else "user_id = ? AND product_id = ? AND variant_id IS NULL"
            params = (user_id, product_id, variant_id) if variant_id else (user_id, product_id)

            existing_item = conn.execute(f"SELECT quantity FROM user_carts WHERE {where_clause}", params).fetchone()
            
            current_in_cart = existing_item['quantity'] if existing_item else 0
            total_requested = current_in_cart + quantity

            if total_requested > available_stock:
                return {'success': False, 'message': f"Stok untuk '{product['name']}' tidak mencukupi (tersisa {available_stock})."}

            if existing_item:
                conn.execute(f"UPDATE user_carts SET quantity = ? WHERE {where_clause}", (total_requested, *params))
            else:
                conn.execute(
                    "INSERT INTO user_carts (user_id, product_id, variant_id, quantity) VALUES (?, ?, ?, ?)",
                    (user_id, product_id, variant_id, quantity)
                )
            conn.commit()
            return {'success': True, 'message': 'Item ditambahkan ke keranjang.'}
        finally:
            conn.close()

    def update_cart_item(self, user_id, product_id, quantity, variant_id=None):
        conn = get_db_connection()
        try:
            where_clause = "user_id = ? AND product_id = ? AND variant_id = ?" if variant_id else "user_id = ? AND product_id = ? AND variant_id IS NULL"
            params = (user_id, product_id, variant_id) if variant_id else (user_id, product_id)
            
            if quantity <= 0:
                conn.execute(f"DELETE FROM user_carts WHERE {where_clause}", params)
            else:
                from services.product_service import product_service
                available_stock = product_service.get_available_stock(product_id, variant_id, conn)

                if quantity > available_stock:
                    return {'success': False, 'message': f'Stok tidak mencukupi. Sisa stok tersedia: {available_stock}.'}
                
                conn.execute(f"UPDATE user_carts SET quantity = ? WHERE {where_clause}", (quantity, *params))
            
            conn.commit()
            return {'success': True}
        finally:
            conn.close()

    def merge_local_cart_to_db(self, user_id, local_cart):
        if not isinstance(local_cart, dict):
            return {'success': False, 'message': 'Format keranjang lokal tidak valid.'}
        
        conn = get_db_connection()
        try:
            with conn:
                from services.product_service import product_service
                for key, data in local_cart.items():
                    parts = key.split('-')
                    product_id = int(parts[0])
                    variant_id = int(parts[1]) if len(parts) > 1 else None
                    quantity = data.get('quantity', 0)
                    
                    if quantity <= 0: continue

                    available_stock = product_service.get_available_stock(product_id, variant_id, conn)
                    if available_stock <= 0: continue

                    where_clause = "user_id = ? AND product_id = ? AND variant_id = ?" if variant_id else "user_id = ? AND product_id = ? AND variant_id IS NULL"
                    params = (user_id, product_id, variant_id) if variant_id else (user_id, product_id)
                    
                    existing_item = conn.execute(f"SELECT quantity FROM user_carts WHERE {where_clause}", params).fetchone()
                    
                    new_quantity = (existing_item['quantity'] if existing_item else 0) + quantity
                    if new_quantity > available_stock: new_quantity = available_stock

                    if existing_item:
                        conn.execute(f"UPDATE user_carts SET quantity = ? WHERE {where_clause}", (new_quantity, *params))
                    else:
                        conn.execute("INSERT INTO user_carts (user_id, product_id, variant_id, quantity) VALUES (?, ?, ?, ?)", (user_id, product_id, variant_id, new_quantity))

            return {'success': True, 'message': 'Keranjang berhasil disinkronkan.'}
        except Exception as e:
            print(f"Error merging cart: {e}")
            return {'success': False, 'message': 'Gagal menyinkronkan keranjang.'}
        finally:
            conn.close()

cart_service = CartService()