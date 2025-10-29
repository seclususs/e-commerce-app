from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.core.db import get_db_connection
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import OutOfStockError, ServiceLogicError
from app.repository.order_item_repository import (
    OrderItemRepository, order_item_repository
)
from app.repository.product_repository import (
    ProductRepository, product_repository
)
from app.repository.stock_repository import StockRepository, stock_repository
from app.repository.variant_repository import (
    VariantRepository, variant_repository
)
from app.services.products.variant_service import (
    VariantService, variant_service
)
from app.utils.logging_utils import get_logger


logger = get_logger(__name__)


class StockService:

    def __init__(
        self,
        stock_repo: StockRepository = stock_repository,
        product_repo: ProductRepository = product_repository,
        variant_repo: VariantRepository = variant_repository,
        order_item_repo: OrderItemRepository = order_item_repository,
        variant_svc: VariantService = variant_service,
    ):
        self.stock_repository = stock_repo
        self.product_repository = product_repo
        self.variant_repository = variant_repo
        self.order_item_repository = order_item_repo
        self.variant_service = variant_svc


    def get_available_stock(
        self,
        product_id: int,
        variant_id: Optional[int] = None,
        conn: Optional[MySQLConnection] = None,
    ) -> int:
        
        stock_check_variant_id = variant_id
        item_id_log = f"Produk {product_id}" + (
            f", Varian {stock_check_variant_id}"
            if stock_check_variant_id is not None
            else ""
        )
        
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
            
        try:
            deleted_count = self.stock_repository.delete_expired(conn)
            if deleted_count > 0:
                if close_conn or not conn.in_transaction:
                    conn.commit()
            else:
                if close_conn or not conn.in_transaction:
                    conn.rollback()
            
            if stock_check_variant_id is not None:
                product_stock_row = self.variant_repository.get_stock(
                    conn, stock_check_variant_id
                )
            else:
                product_stock_row = self.product_repository.get_stock(
                    conn, product_id
                )
            
            if not product_stock_row:
                return 0
            
            product_stock = product_stock_row["stock"]
            held_stock = self.stock_repository.get_held_stock_sum(
                conn, product_id, stock_check_variant_id
            )
            
            available = max(0, product_stock - held_stock)
            return available
        
        except mysql.connector.Error as e:
            raise DatabaseException(
                f"Kesalahan database saat mengambil stok: {e}"
            )
        
        finally:
            if close_conn and conn and conn.is_connected():
                conn.close()


    def hold_stock_for_checkout(
        self,
        user_id: Optional[int],
        session_id: Optional[str],
        cart_items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        
        log_id = f"User {user_id}" if user_id else f"Session {session_id}"
        conn: Optional[MySQLConnection] = None
        
        try:
            conn = get_db_connection()
            conn.start_transaction()
            if user_id:
                deleted_rows = self.stock_repository.delete_by_user_id(
                    conn, user_id
                )
            elif session_id:
                deleted_rows = self.stock_repository.delete_by_session_id(
                    conn, session_id
                )
            else:
                raise ValidationError("User ID atau Session ID diperlukan.")
            
            failed_item_info: Optional[str] = None
            holds_to_insert: List[tuple] = []
            expires_at = datetime.now() + timedelta(minutes=10)

            for item in cart_items:
                product_id = item.get("id") or item.get("product_id")
                variant_id = item.get("variant_id")
                quantity = item.get("quantity")
                item_name = item.get("name", f"ID {product_id}")

                if quantity is None:
                    continue
                item_log_id = f"Produk {product_id}" + (
                    f", Varian {variant_id}" if variant_id is not None else ""
                )
                available_stock = self.get_available_stock(
                    product_id, variant_id, conn
                )

                if quantity > available_stock:
                    size_info = (
                        f" (Ukuran: {item.get('size', 'N/A')})"
                        if item.get("size")
                        else ""
                    )
                    failed_item_info = (
                        f"'{item_name}'{size_info} (tersisa {available_stock})"
                    )
                    raise OutOfStockError(
                        f"Stok untuk {failed_item_info} tidak mencukupi."
                    )
                holds_to_insert.append(
                    (user_id, session_id, product_id, variant_id, quantity, expires_at)
                )
            
            if holds_to_insert:
                rowcount = self.stock_repository.create_batch(
                    conn, holds_to_insert
                )
                
            conn.commit()
            return {"success": True, "expires_at": expires_at.isoformat()}
        
        except OutOfStockError as oose:
            if conn and conn.is_connected():
                conn.rollback()
            return {"success": False, "message": str(oose)}
        
        except ValidationError as ve:
            if conn and conn.is_connected():
                conn.rollback()
            return {"success": False, "message": str(ve)}
        
        except mysql.connector.Error as e:
            if conn and conn.is_connected():
                conn.rollback()
            raise DatabaseException(
                f"Terjadi kesalahan database saat validasi stok: {e}"
            )
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            raise ServiceLogicError(
                f"Terjadi kesalahan saat validasi stok: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def release_stock_holds(
        self,
        user_id: Optional[int],
        session_id: Optional[str],
        conn: MySQLConnection,
    ) -> None:
        
        log_id = f"User {user_id}" if user_id else f"Session {session_id}"

        try:
            if user_id:
                rowcount = self.stock_repository.delete_by_user_id(
                    conn, user_id
                )
            elif session_id:
                rowcount = self.stock_repository.delete_by_session_id(
                    conn, session_id
                )
            else:
                return
        
        except mysql.connector.Error as e:
            raise DatabaseException(
                f"Kesalahan database saat melepaskan penahanan stok: {e}"
            )
        
        except Exception as e:
            raise ServiceLogicError(
                f"Kesalahan layanan saat melepaskan penahanan stok: {e}"
            )
        

    def get_held_items_simple(
        self, user_id: Optional[int], session_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        
        log_id = f"User {user_id}" if user_id else f"Session {session_id}"
        conn: Optional[MySQLConnection] = None
        
        try:
            conn = get_db_connection()
            if user_id:
                held_items = self.stock_repository.find_simple_by_user_id(
                    conn, user_id
                )
            elif session_id:
                held_items = self.stock_repository.find_simple_by_session_id(
                    conn, session_id
                )
            else:
                return []
            return held_items
        
        except mysql.connector.Error as e:
            raise DatabaseException(
                f"Kesalahan database saat mengambil item yang ditahan: {e}"
            )
        
        except Exception as e:
            raise ServiceLogicError(
                f"Kesalahan layanan saat mengambil item yang ditahan: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def restock_items_for_order(
        self, order_id: int, conn: Optional[MySQLConnection]
    ) -> None:
        
        is_external_conn = conn is not None
        if not is_external_conn:
            conn = get_db_connection()
        
        try:
            order_items = self.order_item_repository.find_by_order_id(
                conn, order_id
            )
            if not order_items:
                return
            
            product_ids_with_variants: set[int] = set()

            for item in order_items:
                stock_update_variant_id = item["variant_id"]
                if stock_update_variant_id is not None:
                    rowcount = self.variant_repository.increase_stock(
                        conn, stock_update_variant_id, item["quantity"]
                    )
                    product_ids_with_variants.add(item["product_id"])
                else:
                    rowcount = self.product_repository.increase_stock(
                        conn, item["product_id"], item["quantity"]
                    )
                if rowcount == 0:
                    pass
            
            if product_ids_with_variants:
                for product_id in product_ids_with_variants:
                    self.variant_service.update_total_stock_from_variants(
                        product_id, conn
                    )

        except mysql.connector.Error as e:
            raise DatabaseException(f"Kesalahan database saat restock: {e}")
        
        except Exception as e:
            raise ServiceLogicError(f"Kesalahan layanan saat restock: {e}")
        
        finally:
            if not is_external_conn and conn and conn.is_connected():
                conn.close()

stock_service = StockService(
    stock_repository, product_repository, variant_repository,
    order_item_repository, variant_service
)