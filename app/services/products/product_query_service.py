import json
from app.core.db import get_db_connection
from app.services.orders.stock_service import stock_service
from app.services.products.variant_service import variant_service
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ProductQueryService:
    
    
    def get_filtered_products(self, filters):
        logger.debug(f"Mengambil produk yang difilter dengan filter: {filters}")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            query = (
                "SELECT p.*, c.name AS category_name "
                "FROM products p "
                "LEFT JOIN categories c ON p.category_id = c.id "
                "WHERE 1=1"
            )
            params = []

            if filters.get('search'):
                search_term = f"%{filters['search']}%"
                query += (
                    " AND (p.name LIKE %s OR p.description LIKE %s "
                    "OR p.colors LIKE %s OR c.name LIKE %s)"
                )
                params.extend([search_term, search_term, search_term, search_term])
                logger.debug(f"Menambahkan filter pencarian: {search_term}")

            if filters.get('category'):
                query += " AND p.category_id = %s"
                params.append(filters['category'])
                logger.debug(f"Menambahkan filter kategori: {filters['category']}")

            sort_by = filters.get('sort', 'popularity')
            if sort_by == 'price_asc':
                query += (
                    " ORDER BY CASE "
                    "WHEN p.discount_price IS NOT NULL AND p.discount_price > 0 "
                    "THEN p.discount_price ELSE p.price END ASC"
                )
            elif sort_by == 'price_desc':
                query += (
                    " ORDER BY CASE "
                    "WHEN p.discount_price IS NOT NULL AND p.discount_price > 0 "
                    "THEN p.discount_price ELSE p.price END DESC"
                )
            else:
                query += " ORDER BY p.popularity DESC"

            logger.debug(f"Mengurutkan berdasarkan: {sort_by}")

            cursor.execute(query, tuple(params))
            products = cursor.fetchall()
            logger.info(f"Ditemukan {len(products)} produk yang cocok dengan filter.")
            return products

        except Exception as e:
            logger.error(f"Kesalahan saat memfilter produk: {e}", exc_info=True)
            raise

        finally:
            cursor.close()
            conn.close()
            logger.debug("Koneksi database ditutup untuk get_filtered_products")


    def get_all_products_with_category(self, search=None, category_id=None, stock_status=None):
        logger.debug(
            f"Mengambil semua produk. Pencarian: {search}, "
            f"Kategori: {category_id}, Status Stok: {stock_status}"
        )
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = (
            "SELECT p.*, c.name AS category_name "
            "FROM products p "
            "LEFT JOIN categories c ON p.category_id = c.id"
        )
        params = []
        where_clauses = []

        if search:
            search_term = f"%{search}%"
            where_clauses.append("(p.name LIKE %s OR p.sku LIKE %s)")
            params.extend([search_term, search_term])
            logger.debug(f"Menambahkan filter pencarian: {search_term}")

        if category_id:
            where_clauses.append("p.category_id = %s")
            params.append(category_id)
            logger.debug(f"Menambahkan filter kategori: {category_id}")

        if stock_status == 'in_stock':
            where_clauses.append("p.stock > 5")
        elif stock_status == 'low_stock':
            where_clauses.append("p.stock > 0 AND p.stock <= 5")
        elif stock_status == 'out_of_stock':
            where_clauses.append("p.stock <= 0")

        if stock_status:
            logger.debug(f"Menambahkan filter status stok: {stock_status}")

        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)

        query += " ORDER BY p.id DESC"

        try:
            cursor.execute(query, tuple(params))
            products = cursor.fetchall()
            logger.info(f"Ditemukan {len(products)} produk.")
            return products

        except Exception as e:
            logger.error(f"Kesalahan saat mengambil semua produk: {e}", exc_info=True)
            raise

        finally:
            cursor.close()
            conn.close()
            logger.debug("Koneksi database ditutup untuk get_all_products_with_category")


    def get_product_by_id(self, product_id):
        logger.debug(f"Mengambil produk berdasarkan ID: {product_id}")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(
                "SELECT p.*, c.name AS category_name "
                "FROM products p "
                "LEFT JOIN categories c ON p.category_id = c.id "
                "WHERE p.id = %s",
                (product_id,),
            )
            product = cursor.fetchone()

            if not product:
                logger.warning(f"ID Produk {product_id} tidak ditemukan.")
                return None

            logger.debug(f"Meningkatkan popularitas untuk ID produk {product_id}")
            cursor.execute("UPDATE products SET popularity = popularity + 1 WHERE id = %s", (product_id,))
            conn.commit()

            try:
                product['additional_image_urls'] = (
                    json.loads(product['additional_image_urls'])
                    if product['additional_image_urls']
                    else []
                )
            except (json.JSONDecodeError, TypeError) as json_err:
                logger.warning(
                    f"Gagal mem-parsing additional_image_urls untuk ID produk {product_id}: {json_err}",
                    exc_info=True
                )
                product['additional_image_urls'] = []

            product['all_images'] = [product['image_url']] + product['additional_image_urls']
            product['variants'] = variant_service.get_variants_for_product(product_id, conn)
            logger.debug(f"Mengambil {len(product['variants'])} varian untuk ID produk {product_id}")

            if product['has_variants']:
                for variant in product['variants']:
                    variant['stock'] = stock_service.get_available_stock(product_id, variant['id'], conn)
            else:
                product['stock'] = stock_service.get_available_stock(product_id, None, conn)

            logger.info(f"Detail ID produk {product_id} berhasil diambil.")
            return product

        except Exception as e:
            logger.error(f"Kesalahan saat mengambil ID produk {product_id}: {e}", exc_info=True)
            if conn.is_connected():
                conn.rollback()
            raise

        finally:
            cursor.close()
            conn.close()
            logger.debug(f"Koneksi database ditutup untuk get_product_by_id {product_id}")


    def get_related_products(self, product_id, category_id):
        logger.debug(f"Mengambil produk terkait untuk ID produk: {product_id}, ID kategori: {category_id}")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            query = """
                SELECT p.*, c.name AS category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.category_id = %s AND p.id != %s
                ORDER BY p.popularity DESC
                LIMIT 4
            """
            cursor.execute(query, (category_id, product_id))
            related_products = cursor.fetchall()
            logger.info(f"Ditemukan {len(related_products)} produk terkait untuk ID produk {product_id}")
            return related_products

        except Exception as e:
            logger.error(f"Kesalahan saat mengambil produk terkait untuk ID {product_id}: {e}", exc_info=True)
            raise

        finally:
            cursor.close()
            conn.close()
            logger.debug(f"Koneksi database ditutup untuk get_related_products {product_id}")


product_query_service = ProductQueryService()