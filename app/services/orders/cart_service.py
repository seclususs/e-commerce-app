from decimal import Decimal
from typing import Any, Dict, List, Optional

import mysql.connector

from app.core.db import get_db_connection
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
)
from app.exceptions.service_exceptions import (
    OutOfStockError, ServiceLogicError
)
from app.services.orders.stock_service import stock_service
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class CartService:

    def get_cart_details(self, user_id: int) -> Dict[str, Any]:
        logger.debug(f"Mengambil detail keranjang untuk user_id: {user_id}")

        conn: Optional[Any] = None
        cursor: Optional[Any] = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            query: str = """
                SELECT
                    p.id, p.name, p.price, p.discount_price, p.image_url,
                    p.has_variants, uc.quantity, uc.variant_id,
                    uc.id as cart_item_id, pv.size
                FROM user_carts uc
                JOIN products p ON uc.product_id = p.id
                LEFT JOIN product_variants pv ON uc.variant_id = pv.id
                WHERE uc.user_id = %s
            """

            cursor.execute(query, (user_id,))
            cart_items: List[Dict[str, Any]] = cursor.fetchall()
            logger.info(
                f"Berhasil mengambil {len(cart_items)} item "
                f"untuk user_id: {user_id}"
            )

            subtotal: Decimal = Decimal("0.0")
            items: List[Dict[str, Any]] = []

            for item in cart_items:
                stock_variant_id: Optional[int] = item["variant_id"]
                item["stock"] = stock_service.get_available_stock(
                    item["id"], stock_variant_id, conn
                )

                price = Decimal(str(item["price"])) if item["price"] is not None else Decimal("0.0")
                discount_price = Decimal(str(item["discount_price"])) if item["discount_price"] is not None else Decimal("0.0")

                effective_price: Decimal = (
                    discount_price
                    if discount_price and discount_price > Decimal("0.0")
                    else price
                )

                item["line_total"] = effective_price * Decimal(item["quantity"])
                subtotal += item["line_total"]
                items.append(item)

            logger.debug(
                f"Detail keranjang dihitung untuk user_id: {user_id}. "
                f"Subtotal: {float(subtotal)}"
            )

            return {"items": items, "subtotal": float(subtotal)}

        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat mengambil detail keranjang "
                f"untuk user_id {user_id}: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat mengambil keranjang: {e}"
            )

        except Exception as e:
            logger.error(
                f"Kesalahan saat mengambil detail keranjang "
                f"untuk user_id {user_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat mengambil keranjang: {e}"
            )

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug("Koneksi database ditutup untuk get_cart_details.")


    def add_to_cart(
        self,
        user_id: int,
        product_id: int,
        quantity: int,
        variant_id: Optional[int] = None
    ) -> Dict[str, Any]:
        db_variant_id: Optional[int] = variant_id
        logger.debug(
            f"Mencoba menambahkan ke keranjang untuk user_id: {user_id}. "
            f"Produk: {product_id}, Varian: {db_variant_id}, Jml: {quantity}"
        )

        conn: Optional[Any] = None
        cursor: Optional[Any] = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "SELECT name, has_variants FROM products WHERE id = %s",
                (product_id,)
            )

            product: Optional[Dict[str, Any]] = cursor.fetchone()

            if not product:
                logger.warning(
                    f"Gagal menambahkan ke keranjang: ID Produk {product_id} "
                    f"tidak ditemukan."
                )
                raise RecordNotFoundError("Produk tidak ditemukan.")

            if product["has_variants"] and db_variant_id is None:
                logger.warning(
                    f"Gagal menambahkan ke keranjang: ID Varian diperlukan "
                    f"untuk produk {product_id} tapi None diterima."
                )
                raise ValidationError("Silakan pilih ukuran untuk produk ini.")

            elif not product["has_variants"] and db_variant_id is not None:
                logger.warning(
                    f"Gagal menambahkan ke keranjang: ID Varian {db_variant_id} "
                    f"diberikan untuk produk {product_id} yang tidak "
                    f"bervarian. Mengabaikan variant_id."
                )
                db_variant_id = None

            if db_variant_id is not None:

                cursor.execute(
                    "SELECT id FROM product_variants WHERE id = %s "
                    "AND product_id = %s",
                    (db_variant_id, product_id),
                )

                variant_exists: Optional[Dict[str, Any]] = cursor.fetchone()

                if not variant_exists:
                    logger.warning(
                        f"Gagal menambahkan ke keranjang: Varian ID "
                        f"{db_variant_id} tidak valid/ditemukan untuk "
                        f"Produk ID {product_id}."
                    )
                    raise RecordNotFoundError(
                        "Varian produk yang dipilih tidak valid atau "
                        "tidak ditemukan."
                    )

            available_stock: int = stock_service.get_available_stock(
                product_id, db_variant_id, conn
            )

            logger.debug(
                f"Stok tersedia untuk Produk {product_id}, "
                f"Varian: {db_variant_id}: {available_stock}"
            )

            if db_variant_id is None:
                where_clause: str = (
                    "user_id = %s AND product_id = %s AND variant_id IS NULL"
                )
                params: tuple = (user_id, product_id)

            else:
                where_clause: str = (
                    "user_id = %s AND product_id = %s AND variant_id = %s"
                )
                params = (user_id, product_id, db_variant_id)

            cursor.execute(
                f"SELECT id, quantity FROM user_carts WHERE {where_clause}",
                params
            )

            existing_item: Optional[Dict[str, Any]] = cursor.fetchone()

            current_in_cart: int = (
                existing_item["quantity"] if existing_item else 0
            )
            existing_cart_item_id: Optional[int] = (
                existing_item["id"] if existing_item else None
            )
            total_requested: int = current_in_cart + quantity
            logger.debug(
                f"Pengguna {user_id} meminta {quantity}, sudah memiliki "
                f"{current_in_cart}. Total diminta: {total_requested}"
            )

            if total_requested > available_stock:
                logger.warning(
                    f"Gagal menambahkan ke keranjang: stok tidak mencukupi. "
                    f"Diminta {total_requested}, tersedia {available_stock}"
                )
                raise OutOfStockError(
                    f"Stok untuk '{product['name']}' tidak mencukupi "
                    f"(tersisa {available_stock})."
                )

            cursor.close()
            cursor = conn.cursor()

            if existing_cart_item_id:
                cursor.execute(
                    "UPDATE user_carts SET quantity = %s WHERE id = %s",
                    (total_requested, existing_cart_item_id),
                )
                logger.info(
                    f"Kuantitas diperbarui untuk cart item ID "
                    f"{existing_cart_item_id} menjadi {total_requested}"
                )

            else:
                insert_params: tuple = (
                    user_id, product_id, db_variant_id, quantity
                )

                cursor.execute(
                    """
                    INSERT INTO user_carts
                    (user_id, product_id, variant_id, quantity)
                    VALUES (%s, %s, %s, %s)
                    """,
                    insert_params,
                )
                logger.info(
                    f"Item baru dimasukkan: pengguna {user_id}, "
                    f"produk {product_id}, varian {db_variant_id}, "
                    f"jml {quantity}. ID baru: {cursor.lastrowid}"
                )

            conn.commit()

            return {"success": True, "message": "Item ditambahkan ke keranjang."}

        except (
            ValidationError, RecordNotFoundError, OutOfStockError
        ) as user_error:
            if conn and conn.is_connected():
                conn.rollback()
            logger.warning(
                f"Error adding to cart for user {user_id}, "
                f"product {product_id}, variant {variant_id}: {user_error}"
            )
            return {"success": False, "message": str(user_error)}

        except mysql.connector.Error as db_err:
            if conn and conn.is_connected():
                conn.rollback()

            logger.error(
                f"Kesalahan database saat menambahkan ke keranjang: {db_err}",
                exc_info=True,
            )

            if db_err.errno == 1048 and 'variant_id' in str(db_err).lower():
                logger.error(
                    f"Integrity Error (Col cannot be null) untuk "
                    f"variant_id terdeteksi: {db_err}"
                )
                raise DatabaseException(
                    "Terjadi masalah internal saat memproses varian produk."
                )

            elif db_err.errno == 1062:
                logger.warning(
                    f"Duplicate entry error adding to cart: {db_err}"
                )
                raise DatabaseException("Item ini sudah ada di keranjang Anda.")

            raise DatabaseException(
                f"Kesalahan database saat menambahkan item: {db_err}"
            )

        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan saat menambahkan item ke keranjang untuk "
                f"pengguna {user_id}, produk {product_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(f"Gagal menambahkan item ke keranjang: {e}")

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug("Koneksi database ditutup untuk add_to_cart.")


    def update_cart_item(
        self,
        user_id: int,
        product_id: int,
        quantity: int,
        variant_id: Optional[int] = None
    ) -> Dict[str, Any]:
        db_variant_id: Optional[int] = variant_id
        logger.debug(
            f"Memperbarui item keranjang untuk user_id: {user_id}. "
            f"Produk: {product_id}, Varian: {db_variant_id}, "
            f"Jml Baru: {quantity}"
        )

        conn: Optional[Any] = None
        cursor: Optional[Any] = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            if db_variant_id is None:
                where_clause: str = (
                    "user_id = %s AND product_id = %s AND variant_id IS NULL"
                )
                params: tuple = (user_id, product_id)

            else:
                where_clause: str = (
                    "user_id = %s AND product_id = %s AND variant_id = %s"
                )
                params = (user_id, product_id, db_variant_id)

            cursor.execute(
                f"SELECT id FROM user_carts WHERE {where_clause}", params
            )
            existing_item: Optional[Dict[str, Any]] = cursor.fetchone()

            if not existing_item:
                logger.warning(
                    f"Item keranjang tidak ditemukan untuk pembaruan/penghapusan: "
                    f"user {user_id}, prod {product_id}, var {db_variant_id}"
                )
                raise RecordNotFoundError("Item tidak ditemukan di keranjang.")

            cart_item_id: int = existing_item["id"]
            cursor.close()

            cursor = conn.cursor()

            if quantity <= 0:
                cursor.execute(
                    "DELETE FROM user_carts WHERE id = %s", (cart_item_id,)
                )
                logger.info(
                    f"Item keranjang ID {cart_item_id} dihapus (pengguna "
                    f"{user_id}, produk {product_id}, varian {db_variant_id})"
                )

            else:
                available_stock: int = stock_service.get_available_stock(
                    product_id, db_variant_id, conn
                )
                logger.debug(
                    f"Pemeriksaan stok untuk pembaruan: cart_item_id "
                    f"{cart_item_id}, diminta {quantity}, "
                    f"tersedia {available_stock}"
                )

                if quantity > available_stock:
                    logger.warning(
                        f"Pembaruan gagal untuk cart_item_id {cart_item_id}: "
                        f"stok tidak mencukupi (diminta {quantity}, "
                        f"tersedia {available_stock})"
                    )
                    raise OutOfStockError(
                        "Stok tidak mencukupi. Sisa stok tersedia: "
                        f"{available_stock}."
                    )

                cursor.execute(
                    "UPDATE user_carts SET quantity = %s WHERE id = %s",
                    (quantity, cart_item_id),
                )

                logger.info(
                    f"Kuantitas diperbarui menjadi {quantity} untuk "
                    f"cart item ID {cart_item_id}"
                )

            conn.commit()
            return {"success": True}

        except (OutOfStockError, RecordNotFoundError) as user_error:
            if conn and conn.is_connected():
                conn.rollback()
            return {"success": False, "message": str(user_error)}

        except mysql.connector.Error as db_err:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan database saat memperbarui item keranjang: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat memperbarui item: {db_err}"
            )

        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan saat memperbarui item keranjang: {e}",
                exc_info=True
            )
            raise ServiceLogicError(f"Gagal memperbarui item keranjang: {e}")

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug("Koneksi database ditutup untuk update_cart_item.")


    def merge_local_cart_to_db(
        self, user_id: int, local_cart: Dict[str, Any]
    ) -> Dict[str, Any]:
        logger.debug(
            f"Menggabungkan keranjang lokal ke DB untuk user_id: {user_id}. "
            f"Kunci lokal: {list(local_cart.keys()) if isinstance(local_cart, dict) else 'Tidak Valid'}"
        )

        if not isinstance(local_cart, dict):
            logger.error("Format keranjang yang diterima tidak valid.")
            raise ValidationError("Format keranjang lokal tidak valid.")

        conn: Optional[Any] = None
        cursor: Optional[Any] = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            conn.start_transaction()

            for key, data in local_cart.items():

                try:
                    parts: List[str] = key.split("-")
                    product_id: int = int(parts[0])
                    variant_id_str: str = (
                        parts[1] if len(parts) > 1 else "null"
                    )
                    db_variant_id: Optional[int] = (
                        int(variant_id_str)
                        if variant_id_str.isdigit() else None
                    )
                    quantity: int = data.get("quantity", 0)

                except (ValueError, IndexError) as parse_err:
                    logger.warning(
                        f"Melewatkan kunci yang tidak valid '{key}': "
                        f"{parse_err}"
                    )
                    continue

                if quantity <= 0:
                    continue

                cursor.execute(
                    "SELECT id FROM products WHERE id = %s", (product_id,)
                )

                if not cursor.fetchone():
                    logger.warning(
                        f"Melewatkan item '{key}': Produk ID {product_id} "
                        f"tidak ditemukan."
                    )
                    continue

                if db_variant_id is not None:

                    cursor.execute(
                        "SELECT id FROM product_variants WHERE id = %s "
                        "AND product_id = %s",
                        (db_variant_id, product_id),
                    )

                    if not cursor.fetchone():
                        logger.warning(
                            f"Melewatkan item '{key}': Varian ID "
                            f"{db_variant_id} tidak ditemukan untuk "
                            f"produk {product_id}."
                        )
                        continue

                available_stock: int = stock_service.get_available_stock(
                    product_id, db_variant_id, conn
                )

                if available_stock <= 0:
                    logger.info(
                        f"Melewatkan item '{key}' karena stok habis "
                        f"saat merge."
                    )
                    continue

                if db_variant_id is None:
                    where_clause: str = (
                        "user_id = %s AND product_id = %s AND "
                        "variant_id IS NULL"
                    )
                    params: tuple = (user_id, product_id)

                else:
                    where_clause: str = (
                        "user_id = %s AND product_id = %s AND variant_id = %s"
                    )
                    params = (user_id, product_id, db_variant_id)

                cursor.execute(
                    f"SELECT id, quantity FROM user_carts WHERE {where_clause}",
                    params
                )

                existing_item: Optional[Dict[str, Any]] = cursor.fetchone()
                current_db_quantity: int = (
                    existing_item["quantity"] if existing_item else 0
                )
                existing_cart_item_id: Optional[int] = (
                    existing_item["id"] if existing_item else None
                )
                new_quantity: int = min(
                    current_db_quantity + quantity, available_stock
                )

                temp_cursor: Any = conn.cursor()

                if existing_cart_item_id:
                    temp_cursor.execute(
                        "UPDATE user_carts SET quantity = %s WHERE id = %s",
                        (new_quantity, existing_cart_item_id),
                    )

                else:
                    insert_params: tuple = (
                        user_id, product_id, db_variant_id, new_quantity
                    )
                    temp_cursor.execute(
                        """
                        INSERT INTO user_carts (user_id, product_id,
                        variant_id, quantity)
                        VALUES (%s, %s, %s, %s)
                        """,
                        insert_params,
                    )

                temp_cursor.close()

            conn.commit()
            logger.info("Keranjang lokal berhasil digabungkan.")
            return {"success": True, "message": "Keranjang berhasil disinkronkan."}

        except mysql.connector.Error as db_err:

            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan database saat menggabungkan keranjang: {db_err}",
                exc_info=True,
            )

            if db_err.errno == 1062:
                logger.warning(
                    f"Duplicate entry error during merge: {db_err}"
                )
                raise DatabaseException(
                    "Terjadi konflik saat menggabungkan item keranjang."
                )
            raise DatabaseException(
                f"Kesalahan database saat menggabungkan keranjang: {db_err}"
            )

        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan saat menggabungkan keranjang: {e}", exc_info=True
            )
            raise ServiceLogicError(f"Gagal menyinkronkan keranjang: {e}")

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                "Koneksi database ditutup untuk merge_local_cart_to_db."
            )

    def get_guest_cart_details(
        self, cart_items: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        logger.debug(
            f"Mengambil detail keranjang tamu: {list(cart_items.keys())}"
        )

        product_ids: set[int] = set()
        variant_ids: set[int] = set()
        parsed_cart: Dict[str, Dict[str, Any]] = {}

        for key, item_data in cart_items.items():

            try:
                parts: List[str] = key.split("-")

                if not parts[0].isdigit():
                    continue

                product_id: int = int(parts[0])
                variant_id_str: str = (
                    parts[1] if len(parts) > 1 else "null"
                )
                db_variant_id: Optional[int] = (
                    int(variant_id_str) if variant_id_str.isdigit() else None
                )
                quantity: int = item_data.get("quantity", 0)

                if quantity <= 0:
                    continue

                product_ids.add(product_id)

                if db_variant_id is not None:
                    variant_ids.add(db_variant_id)

                parsed_cart[key] = {
                    "product_id": product_id,
                    "variant_id": db_variant_id,
                    "quantity": quantity,
                }

            except (ValueError, IndexError) as parse_err:
                logger.warning(
                    f"Melewatkan kunci keranjang tamu yang tidak valid "
                    f"'{key}': {parse_err}"
                )
                continue

        if not product_ids:
            logger.info("Keranjang tamu kosong setelah validasi.")
            return []

        conn: Optional[Any] = None
        cursor: Optional[Any] = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            placeholders: str = ", ".join(["%s"] * len(product_ids))
            cursor.execute(
                f"SELECT id, name, price, discount_price, image_url, "
                f"has_variants FROM products WHERE id IN ({placeholders})",
                tuple(product_ids),
            )
            products_db: List[Dict[str, Any]] = cursor.fetchall()
            products_map: Dict[int, Dict[str, Any]] = {
                p["id"]: p for p in products_db
            }
            variants_map: Dict[int, Dict[str, Any]] = {}

            if variant_ids:
                placeholders_v: str = ", ".join(["%s"] * len(variant_ids))
                cursor.execute(
                    f"SELECT id, product_id, size FROM product_variants "
                    f"WHERE id IN ({placeholders_v})",
                    tuple(variant_ids),
                )
                variants_db: List[Dict[str, Any]] = cursor.fetchall()
                variants_map = {v["id"]: v for v in variants_db}

            detailed_items: List[Dict[str, Any]] = []

            for key, parsed_data in parsed_cart.items():
                product_id: int = parsed_data["product_id"]
                db_variant_id: Optional[int] = parsed_data["variant_id"]
                quantity: int = parsed_data["quantity"]
                product_info: Optional[Dict[str, Any]] = (
                    products_map.get(product_id)
                )

                if not product_info:
                    continue

                if (
                    db_variant_id is not None and
                    db_variant_id not in variants_map
                ):
                    continue

                if product_info.get("has_variants") and db_variant_id is None:
                    continue

                final_item: Dict[str, Any] = {**product_info}
                final_item["stock"] = stock_service.get_available_stock(
                    product_id, db_variant_id, conn
                )
                final_item["variant_id"] = db_variant_id
                final_item["size"] = (
                    variants_map[db_variant_id]["size"]
                    if db_variant_id is not None else None
                )
                final_item["quantity"] = quantity

                if final_item["quantity"] > 0:
                    detailed_items.append(final_item)

            logger.info(
                f"Detail keranjang tamu berhasil diambil. "
                f"Item: {len(detailed_items)}"
            )

            return detailed_items

        except mysql.connector.Error as db_err:
            logger.error(
                f"Kesalahan database saat mengambil detail keranjang tamu: "
                f"{db_err}", exc_info=True
            )
            raise DatabaseException(
                f"Kesalahan database saat mengambil keranjang tamu: {db_err}"
            )

        except Exception as e:
            logger.error(
                f"Kesalahan saat mengambil detail keranjang tamu: {e}",
                exc_info=True
            )
            raise ServiceLogicError(f"Gagal mengambil detail keranjang tamu: {e}")

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                "Koneksi database ditutup untuk get_guest_cart_details."
            )

cart_service = CartService()