import json
from db.db_config import get_db_connection
from services.orders.stock_service import stock_service
from services.products.variant_service import variant_service

class ProductQueryService:
    """
    Layanan untuk menangani semua logika query dan filter produk.
    """
    def get_filtered_products(self, filters):
        """Mengambil produk dengan filter, pencarian, dan pengurutan."""
        conn = get_db_connection()
        try:
            query = "SELECT p.*, c.name as category_name FROM products p LEFT JOIN categories c ON p.category_id = c.id WHERE 1=1"
            params = []
            
            if filters.get('search'):
                search_term = f'%{filters["search"]}%'
                query += " AND (p.name LIKE ? OR p.description LIKE ? OR p.colors LIKE ? OR c.name LIKE ?)"
                params.extend([search_term, search_term, search_term, search_term])
            
            if filters.get('category'):
                query += " AND p.category_id = ?"
                params.append(filters['category'])
            
            sort_by = filters.get('sort', 'popularity')
            if sort_by == 'price_asc':
                query += " ORDER BY CASE WHEN p.discount_price IS NOT NULL AND p.discount_price > 0 THEN p.discount_price ELSE p.price END ASC"
            elif sort_by == 'price_desc':
                query += " ORDER BY CASE WHEN p.discount_price IS NOT NULL AND p.discount_price > 0 THEN p.discount_price ELSE p.price END DESC"
            else:
                query += " ORDER BY p.popularity DESC"
                
            products = conn.execute(query, params).fetchall()
            return [dict(p) for p in products]
        finally:
            conn.close()

    def get_all_products_with_category(self, search=None, category_id=None, stock_status=None):
        """Mengambil semua produk beserta nama kategorinya, dengan opsi filter."""
        conn = get_db_connection()
        query = 'SELECT p.*, c.name as category_name FROM products p LEFT JOIN categories c ON p.category_id = c.id'
        params = []
        where_clauses = []

        if search:
            search_term = f'%{search}%'
            where_clauses.append('(p.name LIKE ? OR p.sku LIKE ?)')
            params.extend([search_term, search_term])
        
        if category_id:
            where_clauses.append('p.category_id = ?')
            params.append(category_id)
            
        if stock_status == 'in_stock':
            where_clauses.append('p.stock > 5')
        elif stock_status == 'low_stock':
            where_clauses.append('p.stock > 0 AND p.stock <= 5')
        elif stock_status == 'out_of_stock':
            where_clauses.append('p.stock <= 0')

        if where_clauses:
            query += ' WHERE ' + ' AND '.join(where_clauses)
            
        query += ' ORDER BY p.id DESC'
        
        products = conn.execute(query, params).fetchall()
        conn.close()
        return [dict(p) for p in products]

    def get_product_by_id(self, product_id):
        """Mengambil satu produk berdasarkan ID, termasuk varian dan gambar."""
        conn = get_db_connection()
        try:
            product_row = conn.execute('SELECT p.*, c.name as category_name FROM products p LEFT JOIN categories c ON p.category_id = c.id WHERE p.id = ?', (product_id,)).fetchone()
            if not product_row:
                return None
            
            product = dict(product_row)
            
            # Update popularity
            conn.execute('UPDATE products SET popularity = popularity + 1 WHERE id = ?', (product_id,))
            conn.commit()

            # Proses gambar
            try:
                product['additional_image_urls'] = json.loads(product['additional_image_urls']) if product['additional_image_urls'] else []
            except (json.JSONDecodeError, TypeError):
                product['additional_image_urls'] = []
            product['all_images'] = [product['image_url']] + product['additional_image_urls']
            
            # Panggil service lain untuk data terkait
            product['variants'] = variant_service.get_variants_for_product(product_id, conn)
            if product['has_variants']:
                # Stok total sudah ada di tabel produk, tapi stok tersedia per varian perlu dihitung
                for v in product['variants']:
                    v['stock'] = stock_service.get_available_stock(product_id, v['id'], conn)
            else:
                product['stock'] = stock_service.get_available_stock(product_id, None, conn)

            return product
        finally:
            conn.close()
            
    def get_related_products(self, product_id, category_id):
        """Mengambil produk terkait berdasarkan kategori."""
        conn = get_db_connection()
        try:
            query = """
                SELECT p.*, c.name as category_name 
                FROM products p 
                LEFT JOIN categories c ON p.category_id = c.id 
                WHERE p.category_id = ? AND p.id != ?
                ORDER BY p.popularity DESC 
                LIMIT 4
            """
            related_products = conn.execute(query, (category_id, product_id)).fetchall()
            return [dict(p) for p in related_products]
        finally:
            conn.close()

product_query_service = ProductQueryService()