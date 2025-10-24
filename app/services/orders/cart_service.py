import json
from app.core.db import get_db_connection
from app.services.orders.stock_service import stock_service
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class CartService:


    def get_cart_details(self, user_id):
        logger.debug(f"Mengambil detail keranjang untuk user_id: {user_id}")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            query = """
                SELECT
                    p.id, p.name, p.price, p.discount_price, p.image_url, p.has_variants,
                    uc.quantity, uc.variant_id,
                    pv.size
                FROM user_carts uc
                JOIN products p ON uc.product_id = p.id
                LEFT JOIN product_variants pv ON uc.variant_id = pv.id
                WHERE uc.user_id = %s
            """
            cursor.execute(query, (user_id,))
            cart_items = cursor.fetchall()
            logger.info(f"Berhasil mengambil {len(cart_items)} item untuk user_id: {user_id}")

            subtotal = 0
            items = []

            for item in cart_items:
                item['stock'] = stock_service.get_available_stock(
                    item['id'], item['variant_id'], conn
                )
                effective_price = (
                    item['discount_price']
                    if item['discount_price'] and item['discount_price'] > 0
                    else item['price']
                )
                item['line_total'] = effective_price * item['quantity']
                subtotal += item['line_total']
                items.append(item)

            logger.debug(
                f"Detail keranjang dihitung untuk user_id: {user_id}. Subtotal: {subtotal}"
            )
            return {'items': items, 'subtotal': subtotal}

        except Exception as e:
            logger.error(
                f"Kesalahan saat mengambil detail keranjang untuk user_id {user_id}: {e}",
                exc_info=True
            )
            raise

        finally:
            cursor.close()
            conn.close()
            logger.debug("Koneksi database ditutup untuk get_cart_details.")


    def add_to_cart(self, user_id, product_id, quantity, variant_id=None):
        logger.debug(
            f"Mencoba menambahkan ke keranjang untuk user_id: {user_id}. "
            f"Produk: {product_id}, Varian: {variant_id}, Jml: {quantity}"
        )
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(
                "SELECT name, has_variants FROM products WHERE id = %s",
                (product_id,)
            )
            product = cursor.fetchone()

            if not product:
                logger.warning(
                    f"Gagal menambahkan ke keranjang: ID Produk {product_id} tidak ditemukan."
                )
                return {'success': False, 'message': 'Produk tidak ditemukan.'}

            if product['has_variants'] and not variant_id:
                logger.warning(
                    f"Gagal menambahkan ke keranjang: ID Varian diperlukan untuk produk {product_id}."
                )
                return {
                    'success': False,
                    'message': 'Silakan pilih ukuran untuk produk ini.'
                }

            available_stock = stock_service.get_available_stock(
                product_id, variant_id, conn
            )
            logger.debug(
                f"Stok tersedia untuk Produk {product_id}, "
                f"Varian {variant_id}: {available_stock}"
            )

            where_clause = (
                "user_id = %s AND product_id = %s AND variant_id = %s"
                if variant_id
                else "user_id = %s AND product_id = %s AND variant_id IS NULL"
            )
            params = (
                (user_id, product_id, variant_id)
                if variant_id
                else (user_id, product_id)
            )

            cursor.execute(
                f"SELECT quantity FROM user_carts WHERE {where_clause}",
                params
            )
            existing_item = cursor.fetchone()
            current_in_cart = existing_item['quantity'] if existing_item else 0
            total_requested = current_in_cart + quantity

            logger.debug(
                f"Pengguna {user_id} meminta {quantity}, sudah memiliki {current_in_cart}. "
                f"Total diminta: {total_requested}"
            )

            if total_requested > available_stock:
                logger.warning(
                    f"Gagal menambahkan ke keranjang: stok tidak mencukupi. Diminta {total_requested}, "
                    f"tersedia {available_stock}"
                )
                return {
                    'success': False,
                    'message': f"Stok untuk '{product['name']}' tidak mencukupi "
                               f"(tersisa {available_stock})."
                }

            if existing_item:
                cursor.execute(
                    f"UPDATE user_carts SET quantity = %s WHERE {where_clause}",
                    (total_requested, *params)
                )
                logger.info(
                    f"Kuantitas diperbarui untuk produk {product_id} menjadi {total_requested}"
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO user_carts
                    (user_id, product_id, variant_id, quantity)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (user_id, product_id, variant_id, quantity)
                )
                logger.info(
                    f"Item baru dimasukkan: produk {product_id}, jml {quantity}"
                )

            conn.commit()
            return {'success': True, 'message': 'Item ditambahkan ke keranjang.'}

        except Exception as e:
            conn.rollback()
            logger.error(
                f"Kesalahan saat menambahkan item ke keranjang untuk pengguna {user_id}, produk {product_id}: {e}",
                exc_info=True
            )
            return {
                'success': False,
                'message': 'Gagal menambahkan item ke keranjang.'
            }

        finally:
            cursor.close()
            conn.close()
            logger.debug("Koneksi database ditutup untuk add_to_cart.")


    def update_cart_item(self, user_id, product_id, quantity, variant_id=None):
        logger.debug(
            f"Memperbarui item keranjang untuk user_id: {user_id}. "
            f"Produk: {product_id}, Varian: {variant_id}, Jml Baru: {quantity}"
        )
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            where_clause = (
                "user_id = %s AND product_id = %s AND variant_id = %s"
                if variant_id
                else "user_id = %s AND product_id = %s AND variant_id IS NULL"
            )
            params = (
                (user_id, product_id, variant_id)
                if variant_id
                else (user_id, product_id)
            )

            if quantity <= 0:
                cursor.execute(
                    f"DELETE FROM user_carts WHERE {where_clause}",
                    params
                )
                logger.info(
                    f"Item dihapus: pengguna {user_id}, produk {product_id}"
                )

            else:
                available_stock = stock_service.get_available_stock(
                    product_id, variant_id, conn
                )
                logger.debug(
                    f"Pemeriksaan stok: diminta {quantity}, tersedia {available_stock}"
                )

                if quantity > available_stock:
                    logger.warning(
                        f"Pembaruan gagal: stok tidak mencukupi "
                        f"(diminta {quantity}, tersedia {available_stock})"
                    )
                    return {
                        'success': False,
                        'message': f'Stok tidak mencukupi. '
                                   f'Sisa stok tersedia: {available_stock}.'
                    }

                cursor.execute(
                    f"UPDATE user_carts SET quantity = %s WHERE {where_clause}",
                    (quantity, *params)
                )
                logger.info(
                    f"Kuantitas diperbarui: {quantity} untuk produk {product_id}"
                )

            conn.commit()
            return {'success': True}

        except Exception as e:
            conn.rollback()
            logger.error(
                f"Kesalahan saat memperbarui item keranjang: {e}", exc_info=True
            )
            return {
                'success': False,
                'message': 'Gagal memperbarui item keranjang.'
            }

        finally:
            cursor.close()
            conn.close()
            logger.debug("Koneksi database ditutup untuk update_cart_item.")


    def merge_local_cart_to_db(self, user_id, local_cart):
        logger.debug(
            f"Menggabungkan keranjang lokal ke DB untuk user_id: {user_id}. "
            f"Kunci lokal: {list(local_cart.keys()) if isinstance(local_cart, dict) else 'Tidak Valid'}"
        )

        if not isinstance(local_cart, dict):
            logger.error("Format keranjang yang diterima tidak valid.")
            return {
                'success': False,
                'message': 'Format keranjang lokal tidak valid.'
            }

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            conn.start_transaction()

            for key, data in local_cart.items():
                try:
                    parts = key.split('-')
                    product_id = int(parts[0])
                    variant_id = (
                        int(parts[1])
                        if len(parts) > 1 and parts[1] != 'null'
                        else None
                    )
                    quantity = data.get('quantity', 0)

                except (ValueError, IndexError) as parse_err:
                    logger.warning(
                        f"Melewatkan kunci yang tidak valid '{key}': {parse_err}"
                    )
                    continue

                if quantity <= 0:
                    continue

                available_stock = stock_service.get_available_stock(
                    product_id, variant_id, conn
                )
                if available_stock <= 0:
                    continue

                where_clause = (
                    "user_id = %s AND product_id = %s AND variant_id = %s"
                    if variant_id
                    else "user_id = %s AND product_id = %s AND variant_id IS NULL"
                )
                params = (
                    (user_id, product_id, variant_id)
                    if variant_id
                    else (user_id, product_id)
                )

                cursor.execute(
                    f"SELECT quantity FROM user_carts WHERE {where_clause}",
                    params
                )
                existing_item = cursor.fetchone()
                current_db_quantity = (
                    existing_item['quantity'] if existing_item else 0
                )
                new_quantity = min(
                    current_db_quantity + quantity, available_stock
                )

                if existing_item:
                    cursor.execute(
                        f"UPDATE user_carts SET quantity = %s WHERE {where_clause}",
                        (new_quantity, *params)
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO user_carts
                        (user_id, product_id, variant_id, quantity)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (user_id, product_id, variant_id, new_quantity)
                    )

            conn.commit()
            logger.info("Keranjang lokal berhasil digabungkan.")
            return {'success': True, 'message': 'Keranjang berhasil disinkronkan.'}

        except Exception as e:
            conn.rollback()
            logger.error(
                f"Kesalahan saat menggabungkan keranjang: {e}", exc_info=True
            )
            return {
                'success': False,
                'message': 'Gagal menyinkronkan keranjang.'
            }

        finally:
            cursor.close()
            conn.close()
            logger.debug(
                "Koneksi database ditutup untuk merge_local_cart_to_db."
            )


    def get_guest_cart_details(self, cart_items):
        logger.debug(
            f"Mengambil detail keranjang tamu: {list(cart_items.keys())}"
        )

        product_ids = set()
        variant_ids = set()

        for key in cart_items.keys():
            try:
                parts = key.split('-')

                if parts[0].isdigit():
                    product_ids.add(int(parts[0]))

                if len(parts) > 1 and parts[1].isdigit():
                    variant_ids.add(int(parts[1]))

            except (ValueError, IndexError):
                logger.warning(
                    f"Melewatkan kunci keranjang tamu yang tidak valid '{key}'."
                )
                continue

        if not product_ids:
            logger.info("Keranjang tamu kosong setelah validasi.")
            return []

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            placeholders = ', '.join(['%s'] * len(product_ids))
            cursor.execute(
                f"""
                SELECT id, name, price, discount_price, image_url, has_variants
                FROM products WHERE id IN ({placeholders})
                """,
                tuple(product_ids)
            )
            products_db = cursor.fetchall()
            products_map = {p['id']: p for p in products_db}

            variants_map = {}
            if variant_ids:
                placeholders_v = ', '.join(['%s'] * len(variant_ids))
                cursor.execute(
                    f"""
                    SELECT id, product_id, size
                    FROM product_variants
                    WHERE id IN ({placeholders_v})
                    """,
                    tuple(variant_ids)
                )
                variants_db = cursor.fetchall()
                variants_map = {v['id']: v for v in variants_db}

            detailed_items = []

            for key, item_data in cart_items.items():
                try:
                    parts = key.split('-')
                    product_id = int(parts[0])

                    variant_id = (
                        int(parts[1])
                        if len(parts) > 1 and parts[1].isdigit()
                        else None
                    )
                except (ValueError, IndexError):
                    continue

                product_info = products_map.get(product_id)
                if not product_info:
                    logger.warning(
                        f"ID Produk {product_id} dari keranjang tamu tidak ditemukan."
                    )
                    continue

                final_item = {**product_info}
                final_item['stock'] = stock_service.get_available_stock(
                    product_id, variant_id, conn
                )

                if variant_id and variant_id in variants_map:
                    final_item['variant_id'] = variant_id
                    final_item['size'] = variants_map[variant_id]['size']

                final_item['quantity'] = item_data.get('quantity', 0)

                if final_item['quantity'] > 0:
                    detailed_items.append(final_item)

            logger.info(
                f"Detail keranjang tamu berhasil diambil. Item: {len(detailed_items)}"
            )
            return detailed_items

        except Exception as e:
            logger.error(
                f"Kesalahan saat mengambil detail keranjang tamu: {e}", exc_info=True
            )
            return []

        finally:
            cursor.close()
            conn.close()
            logger.debug(
                "Koneksi database ditutup untuk get_guest_cart_details."
            )


cart_service = CartService()