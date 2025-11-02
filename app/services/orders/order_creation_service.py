from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.core.db import get_db_connection
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
)
from app.exceptions.service_exceptions import OutOfStockError, ServiceLogicError
from app.repository.cart_repository import CartRepository, cart_repository
from app.repository.order_item_repository import (
    OrderItemRepository, order_item_repository
)
from app.repository.order_repository import OrderRepository, order_repository
from app.repository.order_status_history_repository import (
    OrderStatusHistoryRepository, order_status_history_repository
)
from app.repository.product_repository import (
    ProductRepository, product_repository
)
from app.repository.stock_repository import StockRepository, stock_repository
from app.repository.user_voucher_repository import (
    UserVoucherRepository, user_voucher_repository
)
from app.repository.voucher_repository import (
    VoucherRepository, voucher_repository
)
from app.services.orders.discount_service import (
    DiscountService, discount_service
)
from app.services.orders.stock_service import StockService, stock_service
from app.services.orders.voucher_service import (
    VoucherService, voucher_service
)
from app.services.products.variant_service import (
    VariantService, variant_service
)
from app.utils.logging_utils import get_logger


logger = get_logger(__name__)


class OrderCreationService:

    def __init__(
        self,
        stock_repo: StockRepository = stock_repository,
        product_repo: ProductRepository = product_repository,
        order_repo: OrderRepository = order_repository,
        order_item_repo: OrderItemRepository = order_item_repository,
        history_repo: OrderStatusHistoryRepository = (
            order_status_history_repository
        ),
        voucher_repo: VoucherRepository = voucher_repository,
        cart_repo: CartRepository = cart_repository,
        discount_svc: DiscountService = discount_service,
        stock_svc: StockService = stock_service,
        variant_svc: VariantService = variant_service,
        voucher_svc: VoucherService = voucher_service,
        user_voucher_repo: UserVoucherRepository = user_voucher_repository
    ):
        self.stock_repository = stock_repo
        self.product_repository = product_repo
        self.order_repository = order_repo
        self.order_item_repository = order_item_repo
        self.history_repository = history_repo
        self.voucher_repository = voucher_repo
        self.cart_repository = cart_repo
        self.discount_service = discount_svc
        self.stock_service = stock_svc
        self.variant_service = variant_svc
        self.voucher_service = voucher_svc
        self.user_voucher_repository = user_voucher_repo


    def _get_held_items(
        self,
        conn: MySQLConnection,
        user_id: Optional[int],
        session_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        
        log_id = f"User {user_id}" if user_id else f"Session {session_id}"
        logger.debug(f"Mengambil item yang ditahan untuk {log_id}")

        try:
            if user_id:
                result = self.stock_repository.find_detailed_by_user_id(
                    conn, user_id
                )
            elif session_id:
                result = self.stock_repository.find_detailed_by_session_id(
                    conn, session_id
                )
            else:
                logger.error(
                    "Mencoba mengambil item yang ditahan tanpa "
                    "user_id atau session_id."
                )
                raise ValidationError(
                    "User ID atau Session ID diperlukan untuk "
                    "mengambil item yang ditahan."
                )
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


    def _prepare_items_for_order(
        self, conn: MySQLConnection, held_items: List[Dict[str, Any]]
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

        product_ids = [item["product_id"] for item in held_items]
        logger.debug(
            f"Mempersiapkan item untuk pesanan. ID Produk: {product_ids}"
        )
        if not product_ids:
            logger.error(
                "Persiapan item gagal: Daftar item yang ditahan kosong."
            )
            raise ValidationError("Item yang ditahan tidak valid.")

        try:
            products_db = self.product_repository.find_batch_for_order(
                conn, product_ids
            )
            products_map = {p["id"]: p for p in products_db}
            subtotal = Decimal("0")
            items_for_order = []

            for item in held_items:
                product = products_map.get(item["product_id"])
                if not product:
                    logger.error(
                        f"Persiapan item gagal: ID Produk {item['product_id']} "
                        f"(Nama: {item.get('name', 'N/A')}) tidak ditemukan."
                    )
                    raise RecordNotFoundError(
                        f"Produk '{item.get('name', 'N/A')}' "
                        f"tidak lagi tersedia."
                    )

                effective_price = (
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


    def _insert_order_and_items(
        self,
        conn: MySQLConnection,
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
        
        order_id: Optional[int] = None

        try:
            log_id = f"User {user_id}" if user_id else "Guest"
            logger.debug(
                f"Memasukkan catatan pesanan untuk {log_id}. "
                f"Total: {final_total}, Metode: {payment_method}, "
                f"Status: {initial_status}"
            )
            order_id = self.order_repository.create(
                conn,
                user_id,
                subtotal,
                discount_amount,
                shipping_cost,
                final_total,
                voucher_code,
                payment_method,
                transaction_id,
                shipping_details,
            )
            self.history_repository.create(
                conn,
                order_id,
                "Pesanan Dibuat",
                "Pesanan berhasil dibuat oleh pelanggan.",
            )
            items_data = [
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
            self.order_item_repository.create_batch(conn, items_data)
            logger.debug(
                f"Memasukkan {len(items_data)} item pesanan untuk "
                f"ID Pesanan {order_id}"
            )

            if initial_status != "Pesanan Dibuat":
                self.order_repository.update_status(
                    conn, order_id, initial_status
                )
                notes = (
                    "Pembayaran COD dipilih."
                    if payment_method == "COD"
                    else f"Menunggu pembayaran via {payment_method}"
                )
                self.history_repository.create(
                    conn, order_id, initial_status, notes
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


    def _deduct_stock_for_cod_order(
        self,
        conn: MySQLConnection,
        order_id: int,
        items_for_order: List[Dict[str, Any]],
    ) -> None:
        
        product_ids_with_variants: Set[int] = set()

        try:
            for item in items_for_order:
                if item["variant_id"]:
                    lock_id = item["variant_id"]
                    current_stock_row = (
                        self.variant_service.variant_repository.lock_stock(
                            conn, lock_id
                        )
                    )
                else:
                    lock_id = item["id"]
                    current_stock_row = self.product_repository.lock_stock(
                        conn, lock_id
                    )

                if (
                    not current_stock_row
                    or current_stock_row["stock"] < item["quantity"]
                ):
                    raise OutOfStockError(
                        f"Stok habis saat mengurangi untuk "
                        f"{'varian' if item['variant_id'] else 'produk'} "
                        f"ID {lock_id}"
                    )

                if item["variant_id"]:
                    rowcount = (
                        self.variant_service.variant_repository.decrease_stock(
                            conn, lock_id, item["quantity"]
                        )
                    )
                    product_ids_with_variants.add(item["id"])
                else:
                    rowcount = self.product_repository.decrease_stock(
                        conn, lock_id, item["quantity"]
                    )

                if rowcount == 0:
                    raise ServiceLogicError(
                        f"Gagal mengurangi stok COD (rowcount 0) "
                        f"untuk ID {lock_id}"
                    )

            if product_ids_with_variants:
                for pid in product_ids_with_variants:
                    self.variant_service.update_total_stock_from_variants(
                        pid, conn
                    )
            logger.info(
                f"Stok COD berhasil dikurangi untuk pesanan {order_id}"
            )

        except mysql.connector.Error as db_err:
            logger.error(
                f"Kesalahan database saat mengurangi stok COD "
                f"untuk pesanan {order_id}: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat mengurangi stok COD: {db_err}"
            )


    def _post_order_cleanup(
        self,
        conn: MySQLConnection,
        user_id: Optional[int],
        voucher_code: Optional[str],
        user_voucher_id: Optional[int],
        order_id: int,
    ) -> None:
        
        try:
            if voucher_code:
                self.voucher_repository.increment_use_count(
                    conn, voucher_code
                )
                logger.debug(
                    f"Jumlah penggunaan voucher '{voucher_code}' ditingkatkan."
                )

            if user_id and user_voucher_id:
                self.voucher_service.mark_user_voucher_as_used(
                    conn, user_voucher_id, order_id
                )
                logger.debug(
                    f"UserVoucherID {user_voucher_id} ditandai "
                    f"sebagai terpakai."
                )

            if user_id:
                self.cart_repository.clear_user_cart(conn, user_id)
                logger.debug(f"Keranjang pengguna ID {user_id} dikosongkan.")

        except mysql.connector.Error as db_err:
            logger.error(
                f"Kesalahan database saat pembersihan pasca-pesanan "
                f"untuk pengguna {user_id}: {db_err}",
                exc_info=True,
            )


    def create_order(
        self,
        user_id: Optional[int],
        session_id: Optional[str],
        shipping_details: Dict[str, Any],
        payment_method: str,
        voucher_code: Optional[str] = None,
        user_voucher_id_str: Optional[str] = None,
        shipping_cost: float = 0.0,
    ) -> Dict[str, Any]:
        
        log_id = f"User {user_id}" if user_id else f"Session {session_id}"
        logger.info(
            f"Pembuatan pesanan dimulai untuk {log_id}. "
            f"Metode: {payment_method}, Voucher: {voucher_code}, "
            f"UserVoucherID: {user_voucher_id_str}, "
            f"Pengiriman: {shipping_cost}"
        )
        conn: Optional[MySQLConnection] = None
        order_id: Optional[int] = None
        user_voucher_id: Optional[int] = None

        try:
            conn = get_db_connection()
            conn.start_transaction()
            held_items = self._get_held_items(conn, user_id, session_id)
            if not held_items:
                raise ValidationError(
                    "Sesi checkout Anda telah berakhir atau keranjang "
                    "kosong. Silakan kembali ke keranjang."
                )

            items_for_order, subtotal = self._prepare_items_for_order(
                conn, held_items
            )
            discount_amount = Decimal("0")
            final_voucher_code = voucher_code
            
            if user_id and user_voucher_id_str:
                try:
                    user_voucher_id = int(user_voucher_id_str)

                except (ValueError, TypeError):
                    logger.warning(
                        f"user_voucher_id tidak valid: {user_voucher_id_str}"
                    )
                    return {
                        "success": False,
                        "message": "ID Voucher yang dipilih tidak valid.",
                    }
                
                voucher_result = (
                    self.discount_service.validate_and_calculate_by_id(
                        user_id, user_voucher_id, float(subtotal)
                    )
                )

            elif voucher_code:
                voucher_result = (
                    self.discount_service.validate_and_calculate_by_code(
                        voucher_code, float(subtotal)
                    )
                )
            else:
                voucher_result = {"success": False}

            if voucher_result.get("success"):
                discount_amount = Decimal(
                    str(voucher_result["discount_amount"])
                )
                final_voucher_code = voucher_result.get("code")
                user_voucher_id = voucher_result.get("user_voucher_id")

            elif voucher_code or user_voucher_id:
                logger.warning(
                    f"Validasi voucher gagal untuk {log_id}: "
                    f"{voucher_result.get('message')}"
                )
                return {
                    "success": False,
                    "message": voucher_result.get(
                        "message", "Voucher tidak valid."
                    ),
                }

            shipping_cost_decimal = Decimal(str(shipping_cost))
            final_total = (
                subtotal - discount_amount + shipping_cost_decimal
            )
            initial_status = (
                "Diproses"
                if payment_method == "COD"
                else "Menunggu Pembayaran"
            )
            transaction_id = (
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
                final_voucher_code,
                initial_status,
                payment_method,
                transaction_id,
                shipping_details,
                items_for_order
            )
            self._post_order_cleanup(
                conn, user_id, final_voucher_code, user_voucher_id, order_id
            )
            self.stock_service.release_stock_holds(user_id, session_id, conn)
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

order_creation_service = OrderCreationService(
    stock_repository, product_repository, order_repository,
    order_item_repository, order_status_history_repository, voucher_repository,
    cart_repository, discount_service, stock_service, variant_service,
    voucher_service, user_voucher_repository
)