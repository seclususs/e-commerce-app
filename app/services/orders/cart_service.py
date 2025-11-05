from decimal import Decimal
from typing import Any, Dict, List, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.core.db import get_db_connection
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
)
from app.exceptions.service_exceptions import (
    OutOfStockError, ServiceLogicError
)
from app.repository.cart_repository import CartRepository, cart_repository
from app.repository.product_repository import (
    ProductRepository, product_repository
)
from app.repository.variant_repository import (
    VariantRepository, variant_repository
)
from app.services.users.user_service import UserService, user_service
from app.services.orders.stock_service import stock_service


class CartService:

    def __init__(
        self,
        cart_repo: CartRepository = cart_repository,
        product_repo: ProductRepository = product_repository,
        variant_repo: VariantRepository = variant_repository,
        stock_svc: Any = stock_service,
        user_svc: UserService = user_service
    ):
        self.cart_repository = cart_repo
        self.product_repository = product_repo
        self.variant_repository = variant_repo
        self.stock_service = stock_svc
        self.user_service = user_svc


    def get_cart_details(self, user_id: int) -> Dict[str, Any]:

        conn: Optional[MySQLConnection] = None

        try:
            conn = get_db_connection()
            
            subscription = self.user_service.get_active_subscription(user_id, conn)
            member_discount_percent = Decimal("0")
            if subscription and subscription.get("discount_percent"):
                member_discount_percent = Decimal(
                    str(subscription["discount_percent"])
                )

            cart_items = self.cart_repository.get_user_cart_items(conn, user_id)
            subtotal = Decimal("0.0")
            items: List[Dict[str, Any]] = []

            for item in cart_items:
                stock_variant_id = item["variant_id"]
                item["stock"] = self.stock_service.get_available_stock(
                    item["id"], stock_variant_id, conn
                )
                price = (
                    Decimal(str(item["price"]))
                    if item["price"] is not None
                    else Decimal("0.0")
                )
                discount_price = (
                    Decimal(str(item["discount_price"]))
                    if item["discount_price"] is not None
                    else Decimal("0.0")
                )
                effective_price = (
                    discount_price
                    if discount_price and discount_price > Decimal("0.0")
                    else price
                )
                
                if member_discount_percent > 0:
                    discount_amount = (
                        effective_price * (member_discount_percent / Decimal("100"))
                    )
                    item["original_effective_price"] = effective_price
                    effective_price = (effective_price - discount_amount).quantize(
                        Decimal("0.01")
                    )

                item["line_total"] = effective_price * Decimal(item["quantity"])
                subtotal += item["line_total"]
                item["effective_price"] = effective_price
                items.append(item)

            return {"items": items, "subtotal": float(subtotal)}

        except mysql.connector.Error as e:
            raise DatabaseException(
                f"Kesalahan database saat mengambil keranjang: {e}"
            )

        except Exception as e:
            raise ServiceLogicError(
                f"Kesalahan layanan saat mengambil keranjang: {e}"
            )

        finally:
            if conn and conn.is_connected():
                conn.close()


    def add_to_cart(
        self,
        user_id: int,
        product_id: int,
        quantity: int,
        variant_id: Optional[int] = None,
    ) -> Dict[str, Any]:

        db_variant_id = variant_id
        conn: Optional[MySQLConnection] = None

        try:
            conn = get_db_connection()
            conn.start_transaction()
            product = self.product_repository.find_minimal_by_id(
                conn, product_id
            )

            if not product:
                raise RecordNotFoundError("Produk tidak ditemukan.")

            if product["has_variants"] and db_variant_id is None:
                raise ValidationError(
                    "Silakan pilih warna dan ukuran untuk produk ini."
                )

            elif not product["has_variants"]:
                db_variant_id = None

            if db_variant_id is not None:
                variant_exists = self.variant_repository.check_exists(
                    conn, db_variant_id, product_id
                )
                if not variant_exists:
                    raise RecordNotFoundError(
                        "Varian produk yang dipilih tidak valid "
                        "atau tidak ditemukan."
                    )

            available_stock = self.stock_service.get_available_stock(
                product_id, db_variant_id, conn
            )
            existing_item = self.cart_repository.find_cart_item(
                conn, user_id, product_id, db_variant_id
            )
            current_in_cart = existing_item["quantity"] if existing_item else 0
            existing_cart_item_id = (
                existing_item["id"] if existing_item else 0
            )
            total_requested = current_in_cart + quantity

            if total_requested > available_stock:
                raise OutOfStockError(
                    f"Stok untuk '{product['name']}' tidak mencukupi "
                    f"(tersisa {available_stock})."
                )

            if existing_cart_item_id:
                self.cart_repository.update_cart_quantity(
                    conn, existing_cart_item_id, total_requested
                )
            else:
                self.cart_repository.create_cart_item(
                    conn, user_id, product_id, db_variant_id, quantity
                )

            conn.commit()
            return {"success": True, "message": "Item ditambahkan ke keranjang."}

        except (
            ValidationError,
            RecordNotFoundError,
            OutOfStockError
        ) as user_error:
            if conn and conn.is_connected():
                conn.rollback()
            return {"success": False, "message": str(user_error)}

        except mysql.connector.Error as db_err:
            if conn and conn.is_connected():
                conn.rollback()
            if db_err.errno == 1062:
                raise DatabaseException("Item ini sudah ada di keranjang Anda.")
            raise DatabaseException(
                f"Kesalahan database saat menambahkan item: {db_err}"
            )

        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            raise ServiceLogicError(f"Gagal menambahkan item ke keranjang: {e}")

        finally:
            if conn and conn.is_connected():
                conn.close()


    def update_cart_item(
        self,
        user_id: int,
        product_id: int,
        quantity: int,
        variant_id: Optional[int] = None,
    ) -> Dict[str, Any]:

        db_variant_id = variant_id
        conn: Optional[MySQLConnection] = None

        try:
            conn = get_db_connection()
            conn.start_transaction()

            existing_item = self.cart_repository.find_cart_item(
                conn, user_id, product_id, db_variant_id
            )
            if not existing_item:
                raise RecordNotFoundError("Item tidak ditemukan di keranjang.")
            cart_item_id = existing_item["id"]

            if quantity <= 0:
                self.cart_repository.delete_cart_item(conn, cart_item_id)
            else:
                available_stock = self.stock_service.get_available_stock(
                    product_id, db_variant_id, conn
                )
                if quantity > available_stock:
                    raise OutOfStockError(
                        "Stok tidak mencukupi. Sisa stok tersedia: "
                        f"{available_stock}."
                    )
                self.cart_repository.update_cart_quantity(
                    conn, cart_item_id, quantity
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
            raise DatabaseException(
                f"Kesalahan database saat memperbarui item: {db_err}"
            )

        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            raise ServiceLogicError(f"Gagal memperbarui item keranjang: {e}")

        finally:
            if conn and conn.is_connected():
                conn.close()


    def merge_local_cart_to_db(
        self, user_id: int, local_cart: Dict[str, Any]
    ) -> Dict[str, Any]:

        if not isinstance(local_cart, dict):
            raise ValidationError("Format keranjang lokal tidak valid.")

        conn: Optional[MySQLConnection] = None

        try:
            conn = get_db_connection()
            conn.start_transaction()

            for key, data in local_cart.items():
                try:
                    parts = key.split("-")
                    product_id = int(parts[0])
                    variant_id_str = parts[1] if len(parts) > 1 else "null"
                    db_variant_id = (
                        int(variant_id_str)
                        if variant_id_str.isdigit() else None
                    )
                    quantity = data.get("quantity", 0)

                except (ValueError, IndexError):
                    continue

                if quantity <= 0:
                    continue

                product = self.product_repository.find_minimal_by_id(
                    conn, product_id
                )
                if not product:
                    continue

                if db_variant_id is not None:
                    if not self.variant_repository.check_exists(
                        conn, db_variant_id, product_id
                    ):
                        continue

                available_stock = self.stock_service.get_available_stock(
                    product_id, db_variant_id, conn
                )
                if available_stock <= 0:
                    continue

                existing_item = self.cart_repository.find_cart_item(
                    conn, user_id, product_id, db_variant_id
                )
                current_db_quantity = (
                    existing_item["quantity"] if existing_item else 0
                )
                existing_cart_item_id = (
                    existing_item["id"] if existing_item else 0
                )
                new_quantity = min(
                    current_db_quantity + quantity, available_stock
                )

                if existing_cart_item_id:
                    self.cart_repository.update_cart_quantity(
                        conn, existing_cart_item_id, new_quantity
                    )
                else:
                    self.cart_repository.create_cart_item(
                        conn, user_id, product_id, db_variant_id, new_quantity
                    )

            conn.commit()
            return {
                "success": True, "message": "Keranjang berhasil disinkronkan."
            }

        except mysql.connector.Error as db_err:
            if conn and conn.is_connected():
                conn.rollback()
            if db_err.errno == 1062:
                raise DatabaseException(
                    "Terjadi konflik saat menggabungkan item keranjang."
                )
            raise DatabaseException(
                f"Kesalahan database saat menggabungkan keranjang: {db_err}"
            )

        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            raise ServiceLogicError(f"Gagal menyinkronkan keranjang: {e}")

        finally:
            if conn and conn.is_connected():
                conn.close()


    def get_guest_cart_details(
        self, cart_items: Dict[str, Any]
    ) -> List[Dict[str, Any]]:

        product_ids: set[int] = set()
        variant_ids: set[int] = set()
        parsed_cart: Dict[str, Dict[str, Any]] = {}

        for key, item_data in cart_items.items():
            try:
                parts = key.split("-")
                if not parts[0].isdigit():
                    continue

                product_id = int(parts[0])
                variant_id_str = parts[1] if len(parts) > 1 else "null"
                db_variant_id = (
                    int(variant_id_str) if variant_id_str.isdigit() else None
                )
                quantity = item_data.get("quantity", 0)
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

            except (ValueError, IndexError):
                continue

        if not product_ids:
            return []

        conn: Optional[MySQLConnection] = None

        try:
            conn = get_db_connection()
            products_db = self.product_repository.find_batch_minimal(
                conn, list(product_ids)
            )
            products_map = {p["id"]: p for p in products_db}
            variants_map = {}

            if variant_ids:
                variants_db = self.variant_repository.find_batch_minimal(
                    conn, list(variant_ids)
                )
                variants_map = {v["id"]: v for v in variants_db}

            detailed_items = []

            for key, parsed_data in parsed_cart.items():
                product_id = parsed_data["product_id"]
                db_variant_id = parsed_data["variant_id"]
                quantity = parsed_data["quantity"]
                product_info = products_map.get(product_id)
                if not product_info:
                    continue

                if (
                    db_variant_id is not None and
                    db_variant_id not in variants_map
                ):
                    continue

                if product_info.get("has_variants") and db_variant_id is None:
                    continue

                final_item = {**product_info}
                
                price = (
                    Decimal(str(final_item.get("price")))
                    if final_item.get("price") is not None
                    else Decimal("0.0")
                )
                discount_price = (
                    Decimal(str(final_item.get("discount_price")))
                    if final_item.get("discount_price") is not None
                    else Decimal("0.0")
                )
                
                effective_price = (
                    discount_price
                    if discount_price and discount_price > 0
                    else price
                )
                final_item["effective_price"] = effective_price

                final_item["stock"] = self.stock_service.get_available_stock(
                    product_id, db_variant_id, conn
                )
                final_item["variant_id"] = db_variant_id
                final_item["color"] = (
                    variants_map[db_variant_id]["color"]
                    if db_variant_id is not None else None
                )
                final_item["size"] = (
                    variants_map[db_variant_id]["size"]
                    if db_variant_id is not None else None
                )
                final_item["quantity"] = quantity
                if final_item["quantity"] > 0:
                    detailed_items.append(final_item)

            return detailed_items

        except mysql.connector.Error as db_err:
            raise DatabaseException(
                f"Kesalahan database saat mengambil keranjang tamu: {db_err}"
            )

        except Exception as e:
            raise ServiceLogicError(
                f"Gagal mengambil detail keranjang tamu: {e}"
            )

        finally:
            if conn and conn.is_connected():
                conn.close()

cart_service = CartService(
    cart_repository, product_repository, variant_repository, 
    stock_service, user_service
)