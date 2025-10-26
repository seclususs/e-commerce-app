import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

import mysql.connector

from app.core.db import get_db_connection
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import DatabaseException, RecordNotFoundError
from app.exceptions.service_exceptions import OutOfStockError, ServiceLogicError
from app.services.orders.discount_service import discount_service
from app.services.orders.stock_service import stock_service
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class OrderCreationService:

    def _get_held_items(
        self, conn: Any, user_id: Optional[int], session_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        log_id: str = (
            f"User {user_id}" if user_id else f"Session {session_id}"
        )
        logger.debug(f"Mengambil item yang ditahan untuk {log_id}")

        cursor: Any = conn.cursor(dictionary=True)

        try:
            held_items_query: str = """
                SELECT p.id AS product_id, p.name, sh.quantity,
                       sh.variant_id, pv.size
                FROM stock_holds sh
                JOIN products p ON sh.product_id = p.id
                LEFT JOIN product_variants pv ON sh.variant_id = pv.id
                WHERE
            """

            params: List[Any] = []

            if user_id:
                held_items_query += "sh.user_id = %s"
                params.append(user_id)

            elif session_id:
                held_items_query += "sh.session_id = %s"
                params.append(session_id)

            else:
                logger.error(
                    "Mencoba mengambil item yang ditahan tanpa "
                    "user_id atau session_id."
                )
                raise ValidationError(
                    "User ID atau Session ID diperlukan untuk "
                    "mengambil item yang ditahan."
                )

            held_items_query += " AND sh.expires_at > CURRENT_TIMESTAMP"

            cursor.execute(held_items_query, tuple(params))
            result: List[Dict[str, Any]] = cursor.fetchall()
            logger.info(
                f"Menemukan {len(result)} item yang ditahan untuk {log_id}"
            )

            return result

        except mysql.connector.Error as db_err:
            logger.error(
                f"Kesalahan database saat mengambil item yang ditahan "
                f"untuk {log_id}: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                "Kesalahan database saat mengambil item yang "
                f"ditahan: {db_err}"
            )

        finally:
            cursor.close()


    def _prepare_items_for_order(
        self, conn: Any, held_items: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Decimal]:
        if not held_items:
            logger.warning(
                "Persiapan item gagal: Tidak ada item yang ditahan "
                "atau item telah kedaluwarsa."
            )
            raise ValidationError(
                "Sesi checkout Anda telah berakhir atau keranjang kosong. "
                "Silakan kembali ke keranjang."
            )

        product_ids: List[int] = [item["product_id"] for item in held_items]
        logger.debug(
            f"Mempersiapkan item untuk pesanan. ID Produk: {product_ids}"
        )

        if not product_ids:
            logger.error("Persiapan item gagal: Daftar item yang ditahan kosong.")
            raise ValidationError("Item yang ditahan tidak valid.")

        cursor: Any = conn.cursor(dictionary=True)

        try:
            placeholders: str = ", ".join(["%s"] * len(product_ids))

            cursor.execute(
                f"SELECT id, name, price, discount_price "
                f"FROM products WHERE id IN ({placeholders})",
                tuple(product_ids),
            )

            products_db: List[Dict[str, Any]] = cursor.fetchall()

            products_map: Dict[int, Dict[str, Any]] = {
                p["id"]: p for p in products_db
            }
            subtotal: Decimal = Decimal("0")
            items_for_order: List[Dict[str, Any]] = []

            for item in held_items:
                product: Optional[Dict[str, Any]] = products_map.get(
                    item["product_id"]
                )

                if not product:
                    logger.error(
                        f"Persiapan item gagal: ID Produk {item['product_id']} "
                        f"(Nama: {item.get('name', 'N/A')}) tidak ditemukan."
                    )
                    raise RecordNotFoundError(
                        f"Produk '{item.get('name', 'N/A')}' "
                        f"tidak lagi tersedia."
                    )

                effective_price: Decimal = (
                    product["discount_price"]
                    if product["discount_price"]
                    and product["discount_price"] > 0
                    else product["price"]
                )
                subtotal += Decimal(str(effective_price)) * Decimal(
                    str(item["quantity"])
                )
                items_for_order.append(
                    {
                        **product,
                        "quantity": item["quantity"],
                        "price_at_order": effective_price,
                        "variant_id": item["variant_id"],
                        "size": item["size"],
                    }
                )

            logger.info(
                f"Mempersiapkan {len(items_for_order)} item untuk pesanan. "
                f"Subtotal: {subtotal}"
            )

            return items_for_order, subtotal

        except mysql.connector.Error as db_err:
            logger.error(
                f"Kesalahan database saat mempersiapkan item pesanan: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                "Kesalahan database saat mempersiapkan item "
                f"pesanan: {db_err}"
            )

        finally:
            cursor.close()


    def _insert_order_and_items(
        self,
        conn: Any,
        user_id: Optional[int],
        subtotal: Decimal,
        discount_amount: Decimal,
        shipping_cost: Decimal,
        final_total: Decimal,
        voucher_code: Optional[str],
        initial_status: str,
        payment_method: str,
        transaction_id: Optional[str],
        shipping_details: Dict[str, Any],
        items_for_order: List[Dict[str, Any]],
    ) -> int:

        cursor: Any = conn.cursor()
        order_id: Optional[int] = None

        try:
            log_id: str = f"User {user_id}" if user_id else "Guest"
            logger.debug(
                f"Memasukkan catatan pesanan untuk {log_id}. "
                f"Total: {final_total}, Metode: {payment_method}, "
                f"Status: {initial_status}"
            )

            cursor.execute(
                """
                INSERT INTO orders (
                    user_id, subtotal, discount_amount, shipping_cost,
                    total_amount, voucher_code, status, payment_method,
                    payment_transaction_id, shipping_name, shipping_phone,
                    shipping_address_line_1, shipping_address_line_2,
                    shipping_city, shipping_province, shipping_postal_code,
                    shipping_email
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s
                )
                """,
                (
                    user_id,
                    subtotal,
                    discount_amount,
                    shipping_cost,
                    final_total,
                    voucher_code.upper() if voucher_code else None,
                    "Pesanan Dibuat",
                    payment_method,
                    transaction_id,
                    shipping_details["name"],
                    shipping_details["phone"],
                    shipping_details["address1"],
                    shipping_details.get("address2", ""),
                    shipping_details["city"],
                    shipping_details["province"],
                    shipping_details["postal_code"],
                    shipping_details["email"]
                ),
            )

            order_id = cursor.lastrowid

            cursor.execute(
                "INSERT INTO order_status_history (order_id, status, notes) "
                "VALUES (%s, %s, %s)",
                (
                    order_id,
                    "Pesanan Dibuat",
                    "Pesanan berhasil dibuat oleh pelanggan.",
                ),
            )

            items_data: List[tuple] = [
                (
                    order_id,
                    item["id"],
                    item["variant_id"],
                    item["quantity"],
                    item["price_at_order"],
                    item["size"],
                )
                for item in items_for_order
            ]

            cursor.executemany(
                """
                INSERT INTO order_items (
                    order_id, product_id, variant_id, quantity, price,
                    size_at_order
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                items_data,
            )

            logger.debug(
                f"Memasukkan {len(items_data)} item pesanan untuk "
                f"ID Pesanan {order_id}"
            )

            if initial_status != "Pesanan Dibuat":
                cursor.execute(
                    "UPDATE orders SET status = %s WHERE id = %s",
                    (initial_status, order_id),
                )
                notes: str = (
                    "Pembayaran COD dipilih."
                    if payment_method == "COD"
                    else f"Menunggu pembayaran via {payment_method}"
                )
                cursor.execute(
                    "INSERT INTO order_status_history (order_id, status, "
                    "notes) VALUES (%s, %s, %s)",
                    (order_id, initial_status, notes),
                )

            if payment_method == "COD":
                self._deduct_stock_for_cod_order(
                    conn, order_id, items_for_order
                )

            return order_id

        except mysql.connector.Error as db_err:
            logger.error(
                f"Kesalahan database saat penyisipan pesanan untuk "
                f"ID Pesanan {order_id or 'baru'}: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat menyimpan pesanan: {db_err}"
            )

        finally:
            cursor.close()


    def _deduct_stock_for_cod_order(
        self, conn: Any, order_id: int, items_for_order: List[Dict[str, Any]]
    ) -> None:
        cursor: Any = conn.cursor()
        product_ids_with_variants: Set[int] = set()

        try:
            for item in items_for_order:
                lock_query: str = (
                    "SELECT stock FROM product_variants WHERE id = %s FOR UPDATE"
                    if item["variant_id"]
                    else "SELECT stock FROM products WHERE id = %s FOR UPDATE"
                )
                lock_id: int = (
                    item["variant_id"]
                    if item["variant_id"]
                    else item["id"]
                )

                cursor.execute(lock_query, (lock_id,))
                current_stock_row: Optional[tuple] = cursor.fetchone()

                if not current_stock_row or current_stock_row[0] < item["quantity"]:
                    raise OutOfStockError(
                        f"Stok habis saat mengurangi untuk "
                        f"{'varian' if item['variant_id'] else 'produk'} "
                        f"ID {lock_id}"
                    )

                update_query: str = (
                    "UPDATE {} SET stock = stock - %s WHERE id = %s"
                ).format(
                    "product_variants" if item["variant_id"] else "products"
                )
                update_id: int = lock_id
                cursor.execute(update_query, (item["quantity"], update_id))

                if cursor.rowcount == 0:
                    raise ServiceLogicError(
                        f"Gagal mengurangi stok COD (rowcount 0) "
                        f"untuk ID {update_id}"
                    )

                if item["variant_id"]:
                    product_ids_with_variants.add(item["id"])

            self._update_total_stock_after_variant_updates(
                conn, product_ids_with_variants
            )
            logger.info(f"Stok COD berhasil dikurangi untuk pesanan {order_id}")

        except mysql.connector.Error as db_err:
            logger.error(
                f"Kesalahan database saat mengurangi stok COD "
                f"untuk pesanan {order_id}: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat mengurangi stok COD: {db_err}"
            )

        finally:
            cursor.close()


    def _update_total_stock_after_variant_updates(
        self, conn: Any, product_ids: Set[int]
    ) -> None:
        if not product_ids:
            return
        cursor: Any = conn.cursor(dictionary=True)

        try:
            for product_id in product_ids:

                cursor.execute(
                    "SELECT SUM(stock) AS total FROM product_variants "
                    "WHERE product_id = %s",
                    (product_id,),
                )

                total_stock_row: Optional[Dict[str, Any]] = cursor.fetchone()

                total_stock: int = (
                    total_stock_row["total"] if total_stock_row and
                    total_stock_row['total'] is not None else 0
                )

                cursor.execute(
                    "UPDATE products SET stock = %s WHERE id = %s",
                    (total_stock, product_id),
                )

            logger.info(f"Total stok produk diperbarui untuk ID: {product_ids}")

        except mysql.connector.Error as db_err:
            logger.error(
                f"Kesalahan database saat memperbarui stok total produk "
                f"{product_ids}: {db_err}",
                exc_info=True,
            )

        finally:
            cursor.close()

    def _post_order_cart_cleanup(
        self, conn: Any, user_id: Optional[int], voucher_code: Optional[str]
    ) -> None:
        
        cursor: Any = conn.cursor()

        try:
            if voucher_code:
                cursor.execute(
                    "UPDATE vouchers SET use_count = use_count + 1 "
                    "WHERE code = %s",
                    (voucher_code.upper(),),
                )
                logger.debug(
                    f"Jumlah penggunaan voucher '{voucher_code}' ditingkatkan."
                )

            if user_id:
                cursor.execute(
                    "DELETE FROM user_carts WHERE user_id = %s", (user_id,)
                )
                logger.debug(f"Keranjang pengguna ID {user_id} dikosongkan.")

        except mysql.connector.Error as db_err:
            logger.error(
                f"Kesalahan database saat pembersihan pasca-pesanan "
                f"untuk pengguna {user_id}: {db_err}",
                exc_info=True,
            )

        finally:
            cursor.close()


    def create_order(
        self,
        user_id: Optional[int],
        session_id: Optional[str],
        shipping_details: Dict[str, Any],
        payment_method: str,
        voucher_code: Optional[str] = None,
        shipping_cost: float = 0.0,
    ) -> Dict[str, Any]:
        log_id: str = (
            f"User {user_id}" if user_id else f"Session {session_id}"
        )
        logger.info(
            f"Pembuatan pesanan dimulai untuk {log_id}. "
            f"Metode: {payment_method}, Voucher: {voucher_code}, "
            f"Pengiriman: {shipping_cost}"
        )

        conn: Optional[Any] = None
        order_id: Optional[int] = None

        try:
            conn = get_db_connection()
            conn.start_transaction()

            held_items: List[Dict[str, Any]] = self._get_held_items(
                conn, user_id, session_id
            )

            if not held_items:
                raise ValidationError(
                    "Sesi checkout Anda telah berakhir atau keranjang "
                    "kosong. Silakan kembali ke keranjang."
                )

            items_for_order: List[Dict[str, Any]]
            subtotal: Decimal
            items_for_order, subtotal = self._prepare_items_for_order(
                conn, held_items
            )
            discount_amount: Decimal = Decimal("0")

            if voucher_code:
                voucher_result: Dict[str, Any] = (
                    discount_service.validate_and_calculate_voucher(
                        voucher_code, float(subtotal)
                    )
                )

                if voucher_result["success"]:
                    discount_amount = Decimal(
                        str(voucher_result["discount_amount"])
                    )

                else:
                    raise ValidationError(voucher_result["message"])

            shipping_cost_decimal: Decimal = Decimal(str(shipping_cost))
            final_total: Decimal = (
                subtotal - discount_amount + shipping_cost_decimal
            )
            initial_status: str = (
                "Diproses"
                if payment_method == "COD"
                else "Menunggu Pembayaran"
            )
            transaction_id: Optional[str] = (
                f"TX-{uuid.uuid4().hex[:8].upper()}"
                if initial_status == "Menunggu Pembayaran"
                else None
            )

            order_id = self._insert_order_and_items(
                conn,
                user_id,
                subtotal,
                discount_amount,
                shipping_cost_decimal,
                final_total,
                voucher_code,
                initial_status,
                payment_method,
                transaction_id,
                shipping_details,
                items_for_order,
            )

            self._post_order_cart_cleanup(conn, user_id, voucher_code)

            stock_service.release_stock_holds(user_id, session_id, conn)

            conn.commit()

            logger.info(
                f"Pesanan #{order_id} berhasil dibuat untuk {log_id}."
            )

            return {"success": True, "order_id": order_id}

        except (ValidationError, RecordNotFoundError, OutOfStockError) as ve:
            if conn and conn.is_connected():
                conn.rollback()
            logger.warning(
                f"Pembuatan pesanan gagal untuk {log_id} karena "
                f"validasi/error: {ve}"
            )
            return {"success": False, "message": str(ve)}

        except (mysql.connector.Error, DatabaseException) as db_err:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan database saat membuat pesanan untuk {log_id}: "
                f"{db_err}",
                exc_info=True,
            )
            return {
                "success": False,
                "message": "Terjadi kesalahan database saat membuat pesanan.",
            }

        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan tak terduga saat membuat pesanan untuk {log_id}: {e}",
                exc_info=True,
            )
            return {
                "success": False,
                "message": "Terjadi kesalahan internal saat membuat pesanan.",
            }

        finally:
            if conn and conn.is_connected():
                conn.close()
                logger.debug(
                    f"Koneksi database ditutup untuk create_order {log_id}"
                )

order_creation_service = OrderCreationService()