from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid

import mysql.connector
from mysql.connector.connection import MySQLConnection
from dateutil.relativedelta import relativedelta

from app.core.db import get_db_connection
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
)
from app.exceptions.service_exceptions import (
    ServiceLogicError, InvalidOperationError
)
from app.repository.membership_repository import (
    MembershipRepository, membership_repository
)
from app.repository.order_repository import OrderRepository, order_repository
from app.repository.user_repository import UserRepository, user_repository
from app.repository.order_status_history_repository import (
    OrderStatusHistoryRepository, order_status_history_repository
)
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class MembershipService:

    def __init__(
        self,
        membership_repo: MembershipRepository = membership_repository,
        order_repo: OrderRepository = order_repository,
        user_repo: UserRepository = user_repository,
        history_repo: OrderStatusHistoryRepository = order_status_history_repository
    ):
        self.membership_repository = membership_repo
        self.order_repository = order_repo
        self.user_repository = user_repo
        self.history_repository = history_repo


    def _validate_and_prepare_data(
        self, form_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        
        try:
            name = form_data.get("name")
            if not name or not name.strip():
                raise ValidationError("Nama paket tidak boleh kosong.")

            price = Decimal(form_data.get("price", 0))
            if price <= 0:
                raise ValidationError("Harga harus lebih besar dari nol.")

            period = form_data.get("period")
            if period not in ['monthly', 'yearly']:
                raise ValidationError("Periode harus 'monthly' atau 'yearly'.")

            discount = Decimal(form_data.get("discount_percent", 0))
            if not (0 <= discount <= 100):
                raise ValidationError("Diskon persentase harus antara 0 dan 100.")

            return {
                "name": name.strip(),
                "price": price,
                "period": period,
                "discount_percent": discount,
                "free_shipping": 1 if "free_shipping" in form_data else 0,
                "is_active": 1 if "is_active" in form_data else 0,
                "description": form_data.get("description", "").strip() or None
            }
        
        except (InvalidOperation, TypeError, ValueError) as e:
            logger.warning(
                f"Validasi data membership gagal: {e}", 
                exc_info=True
                )
            raise ValidationError(
                "Format data tidak valid untuk harga atau diskon."
                )


    def get_all_memberships_for_admin(self) -> List[Dict[str, Any]]:
        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            return self.membership_repository.find_all_memberships(conn)
        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat mengambil semua membership: {e}", exc_info=True
            )
            raise DatabaseException(
                "Kesalahan database saat mengambil daftar membership."
            )
        finally:
            if conn and conn.is_connected():
                conn.close()

    def get_all_active_memberships(self) -> List[Dict[str, Any]]:
        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            return self.membership_repository.find_all_active_memberships(conn)
        
        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat mengambil membership aktif: {e}", 
                exc_info=True
            )
            raise DatabaseException(
                "Kesalahan database saat mengambil daftar membership."
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def create_membership(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        conn: Optional[MySQLConnection] = None
        try:
            data = self._validate_and_prepare_data(form_data)
            conn = get_db_connection()
            conn.start_transaction()
            new_id = self.membership_repository.create_membership(conn, data)
            conn.commit()
            
            new_membership = self.membership_repository.find_membership_by_id(
                conn, new_id
            )
            return {
                "success": True,
                "message": "Paket membership berhasil dibuat.",
                "data": new_membership
            }
        
        except (ValidationError, DatabaseException) as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.warning(
                f"Gagal membuat membership: {e}", 
                exc_info=True
            )
            return {"success": False, "message": str(e)}
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan tak terduga saat membuat membership: {e}", 
                exc_info=True
            )
            raise ServiceLogicError(
                "Gagal membuat membership karena kesalahan server."
                )
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def update_membership(
        self, membership_id: int, form_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        conn: Optional[MySQLConnection] = None
        try:
            data = self._validate_and_prepare_data(form_data)
            conn = get_db_connection()
            conn.start_transaction()
            
            rowcount = self.membership_repository.update_membership(
                conn, membership_id, data
            )
            if rowcount == 0:
                raise RecordNotFoundError("Paket membership tidak ditemukan.")

            conn.commit()
            updated_membership = self.membership_repository.find_membership_by_id(
                conn, membership_id
            )
            return {
                "success": True,
                "message": "Paket membership berhasil diperbarui.",
                "data": updated_membership
            }
        
        except (ValidationError, RecordNotFoundError, DatabaseException) as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.warning(
                f"Gagal memperbarui membership {membership_id}: {e}", 
                exc_info=True
            )
            return {"success": False, "message": str(e)}
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan tak terduga saat memperbarui membership {membership_id}: {e}",
                exc_info=True
            )
            raise ServiceLogicError(
                "Gagal memperbarui membership karena kesalahan server."
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def delete_membership(self, membership_id: int) -> Dict[str, Any]:
        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            conn.start_transaction()
            
            rowcount = self.membership_repository.delete_membership(
                conn, membership_id
            )
            if rowcount == 0:
                raise RecordNotFoundError("Paket membership tidak ditemukan.")

            conn.commit()
            return {"success": True, "message": "Paket membership berhasil dihapus."}
        
        except mysql.connector.IntegrityError as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.warning(
                f"Gagal menghapus membership {membership_id} karena FK constraint: {e}"
            )
            return {
                "success": False,
                "message": (
                    "Tidak dapat menghapus paket ini karena masih ada "
                    "pelanggan yang berlangganan."
                )
            }
        
        except (RecordNotFoundError, DatabaseException) as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.warning(
                f"Gagal menghapus membership {membership_id}: {e}", 
                exc_info=True
            )
            return {"success": False, "message": str(e)}
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan tak terduga saat menghapus membership {membership_id}: {e}",
                exc_info=True
            )
            raise ServiceLogicError(
                "Gagal menghapus membership karena kesalahan server."
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def subscribe_to_plan(
        self, user_id: int, membership_id: int
    ) -> Dict[str, Any]:
        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            conn.start_transaction()

            current_subscription = (
                self.membership_repository.find_active_subscription_by_user_id(
                    conn, user_id
                )
            )
            if current_subscription:
                raise InvalidOperationError(
                    "Anda sudah memiliki paket aktif. "
                    "Silakan upgrade jika tersedia."
                )
            
            new_plan = self.membership_repository.find_membership_by_id(
                conn, membership_id
            )
            if not new_plan or not new_plan["is_active"]:
                raise RecordNotFoundError(
                    "Paket membership tidak ditemukan atau tidak aktif."
                    )
            
            user = self.user_repository.find_by_id(conn, user_id)
            if not user:
                raise RecordNotFoundError("Pengguna tidak ditemukan.")

            payment_transaction_id = f"TX-MEM-{uuid.uuid4().hex[:8].upper()}"
            shipping_details = {
                "name": user.get("username"),
                "email": user.get("email"),
                "phone": user.get("phone", ""),
                "address1": user.get("address_line_1", ""),
                "address2": user.get("address_line_2", ""),
                "city": user.get("city", ""),
                "province": user.get("province", ""),
                "postal_code": user.get("postal_code", ""),
            }
            
            notes = f"MEMBERSHIP_PURCHASE:{membership_id}"

            order_id = self.order_repository.create(
                conn,
                user_id,
                new_plan["price"],
                Decimal("0"),
                Decimal("0"),
                new_plan["price"],
                None,
                "Virtual Account",
                payment_transaction_id,
                shipping_details,
                notes=notes
            )

            self.order_repository.update_status(
                conn, order_id, "Menunggu Pembayaran"
            )
            self.history_repository.create(
                conn, order_id, "Menunggu Pembayaran", notes
            )
            
            conn.commit()
            logger.info(
                f"Pesanan {order_id} dibuat untuk langganan paket {new_plan['name']} oleh pengguna {user_id}"
                )
            return {
                "success": True,
                "order_id": order_id
            }

        except (InvalidOperationError, RecordNotFoundError) as e:
            if conn: conn.rollback()
            return {"success": False, "message": str(e)}
        
        except mysql.connector.Error as e:
            if conn: conn.rollback()
            logger.error(
                f"DB Error saat subscribe: {e}", 
                exc_info=True
                )
            raise DatabaseException(
                "Gagal mendaftar paket karena kesalahan database."
                )
        
        except Exception as e:
            if conn: conn.rollback()
            logger.error(
                f"Error tak terduga saat subscribe: {e}", 
                exc_info=True
                )
            raise ServiceLogicError(
                "Gagal mendaftar paket karena kesalahan server."
                )
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def upgrade_subscription(
        self, user_id: int, new_membership_id: int
    ) -> Dict[str, Any]:
        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            conn.start_transaction()

            current_subscription = (
                self.membership_repository.find_active_subscription_by_user_id(
                    conn, user_id
                )
            )
            if not current_subscription:
                raise InvalidOperationError(
                    "Anda tidak memiliki langganan aktif untuk di-upgrade."
                    )
            
            if current_subscription["period"] != 'monthly':
                raise InvalidOperationError(
                    "Hanya paket bulanan yang bisa di-upgrade."
                    )

            new_plan = self.membership_repository.find_membership_by_id(
                conn, new_membership_id
            )
            if not new_plan or not new_plan["is_active"]:
                raise RecordNotFoundError(
                    "Paket upgrade tidak ditemukan atau tidak aktif."
                    )
            
            if new_plan["period"] != 'yearly':
                raise InvalidOperationError(
                    "Upgrade hanya bisa dilakukan ke paket tahunan."
                    )

            now = datetime.now()
            current_start = current_subscription["start_date"]
            current_end = current_subscription["end_date"]
            
            if now > current_end:
                 raise InvalidOperationError(
                     "Langganan Anda saat ini sudah berakhir."
                     )

            days_in_cycle = (current_end - current_start).days
            if days_in_cycle <= 0: days_in_cycle = 30 
            
            days_remaining = (current_end - now).days
            if days_remaining < 0: days_remaining = 0
            
            current_price = Decimal(current_subscription["price"])
            price_per_day = current_price / Decimal(days_in_cycle)
            remaining_value = price_per_day * Decimal(days_remaining)
            
            new_price = Decimal(new_plan["price"])
            prorated_price = new_price - remaining_value
            if prorated_price < 0:
                prorated_price = Decimal("0")

            prorated_price = prorated_price.quantize(Decimal("0.01"))
            
            user = self.user_repository.find_by_id(conn, user_id)
            if not user:
                raise RecordNotFoundError("Pengguna tidak ditemukan.")

            payment_transaction_id = f"TX-UPG-{uuid.uuid4().hex[:8].upper()}"
            shipping_details = {
                "name": user.get("username"),
                "email": user.get("email"),
                "phone": user.get("phone", ""),
                "address1": user.get("address_line_1", ""),
                "address2": user.get("address_line_2", ""),
                "city": user.get("city", ""),
                "province": user.get("province", ""),
                "postal_code": user.get("postal_code", ""),
            }

            notes = f"MEMBERSHIP_UPGRADE:{new_membership_id}:SUB_ID:{current_subscription['user_subscription_id']}"

            order_id = self.order_repository.create(
                conn,
                user_id,
                prorated_price,
                Decimal("0"),
                Decimal("0"),
                prorated_price,
                None,
                "Virtual Account",
                payment_transaction_id,
                shipping_details,
                notes=notes
            )

            self.order_repository.update_status(
                conn, order_id, "Menunggu Pembayaran"
            )
            self.history_repository.create(
                conn, order_id, "Menunggu Pembayaran", notes
            )
            
            conn.commit()
            logger.info(
                f"Pesanan {order_id} dibuat untuk upgrade ke {new_plan['name']}. Biaya: {prorated_price}"
                )
            return {
                "success": True,
                "order_id": order_id
            }

        except (InvalidOperationError, RecordNotFoundError) as e:
            if conn: conn.rollback()
            return {"success": False, "message": str(e)}
        
        except mysql.connector.Error as e:
            if conn: conn.rollback()
            logger.error(
                f"DB Error saat upgrade: {e}", 
                exc_info=True
                )
            raise DatabaseException(
                "Gagal upgrade paket karena kesalahan database."
                )
        
        except Exception as e:
            if conn: conn.rollback()
            logger.error(
                f"Error tak terduga saat upgrade: {e}", 
                exc_info=True
                )
            raise ServiceLogicError(
                "Gagal upgrade paket karena kesalahan server."
                )
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def activate_subscription_from_order(
        self, conn: MySQLConnection, user_id: int, 
        membership_id: int, amount_paid: Decimal
    ) -> None:
        
        new_plan = self.membership_repository.find_membership_by_id(
            conn, membership_id
        )
        if not new_plan:
            raise RecordNotFoundError(
                f"Paket membership {membership_id} tidak ditemukan saat aktivasi."
                )
            
        now = datetime.now()
        end_date = (
            now + relativedelta(years=1)
            if new_plan["period"] == "yearly"
            else now + relativedelta(months=1)
        )
            
        self.membership_repository.create_subscription(
            conn, user_id, membership_id, now, end_date, 'active'
        )
            
        self.membership_repository.create_transaction(
            conn, user_id, membership_id, 'new', amount_paid,
            f"Pembelian baru paket {new_plan['name']}"
        )
        logger.info(
            f"Langganan {new_plan['name']} diaktifkan untuk pengguna {user_id}."
            )


    def activate_upgrade_from_order(
        self, conn: MySQLConnection, user_id: int, 
        new_membership_id: int, user_subscription_id: int, 
        amount_paid: Decimal
    ) -> None:

        current_subscription = (
            self.membership_repository.find_active_subscription_by_user_id(
                conn, user_id
            )
        )
        if not current_subscription or current_subscription["user_subscription_id"] != user_subscription_id:
            raise InvalidOperationError(
                "Langganan aktif tidak ditemukan atau tidak cocok saat upgrade."
                )
            
        new_plan = self.membership_repository.find_membership_by_id(
            conn, new_membership_id
        )
        if not new_plan:
            raise RecordNotFoundError(
                f"Paket upgrade {new_membership_id} tidak ditemukan saat aktivasi."
                )

        now = datetime.now()
        new_end_date = now + relativedelta(years=1)
            
        self.membership_repository.update_subscription(
            conn,
            user_subscription_id,
            new_membership_id,
            now,
            new_end_date,
            'active'
        )
            
        notes = (
            f"Upgrade dari {current_subscription['name']} ke {new_plan['name']}. "
            f"Total Bayar: {amount_paid}"
        )
        self.membership_repository.create_transaction(
            conn, user_id, new_membership_id, 'upgrade', amount_paid, notes
        )
        logger.info(
            f"Langganan pengguna {user_id} diupgrade ke {new_plan['name']}."
            )

membership_service = MembershipService(
    membership_repository, order_repository, user_repository,
    order_status_history_repository
)