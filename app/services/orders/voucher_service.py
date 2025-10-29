from decimal import Decimal
from typing import Any, Dict, List, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.core.db import get_db_connection
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
)
from app.exceptions.service_exceptions import ServiceLogicError
from app.repository.voucher_repository import (
    VoucherRepository, voucher_repository
)


class VoucherService:

    def __init__(self, voucher_repo: VoucherRepository = voucher_repository):
        self.voucher_repository = voucher_repo


    def get_active_voucher_by_code(
        self, code: str
    ) -> Optional[Dict[str, Any]]:
        
        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            return self.voucher_repository.find_active_by_code(conn, code)
        
        except mysql.connector.Error as e:
            raise DatabaseException(
                f"Kesalahan database saat mengambil voucher: {e}"
            )
        
        except Exception as e:
            raise ServiceLogicError(
                f"Kesalahan layanan saat mengambil voucher: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def get_all_vouchers(self) -> List[Dict[str, Any]]:

        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            return self.voucher_repository.find_all(conn)
        
        except mysql.connector.Error as e:
            raise DatabaseException(
                f"Kesalahan database saat mengambil voucher: {e}"
            )
        
        except Exception as e:
            raise ServiceLogicError(
                f"Kesalahan layanan saat mengambil voucher: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def add_voucher(
        self,
        code: str,
        voucher_type: str,
        value: str,
        min_purchase: Optional[str],
        max_uses: Optional[str],
    ) -> Dict[str, Any]:
        
        standardized_code = code.upper().strip()
        if not standardized_code or not voucher_type or not value:
            raise ValidationError("Kode, Tipe, dan Nilai tidak boleh kosong.")

        conn: Optional[MySQLConnection] = None

        try:
            value_decimal = Decimal(str(value))
            min_purchase_decimal = (
                Decimal(str(min_purchase))
                if min_purchase
                else Decimal("0")
            )
            max_uses_int = int(max_uses) if max_uses else None

            if (voucher_type == "PERCENTAGE" and not (0 <= value_decimal <= 100)):
                raise ValidationError("Persentase harus antara 0 dan 100.")
            
            if voucher_type == "FIXED_AMOUNT" and value_decimal < 0:
                raise ValidationError("Jumlah tetap tidak boleh negatif.")
            
            if min_purchase_decimal < 0:
                raise ValidationError("Minimal pembelian tidak boleh negatif.")
            
            if max_uses_int is not None and max_uses_int < 0:
                raise ValidationError(
                    "Maksimum penggunaan tidak boleh negatif."
                )

            conn = get_db_connection()
            conn.start_transaction()
            existing_voucher = self.voucher_repository.find_by_code(
                conn, standardized_code
            )
            if existing_voucher:
                conn.rollback()
                return {
                    "success": False,
                    "message": f'Kode voucher "{standardized_code}" '
                               f'sudah terdaftar.',
                }
            
            new_id = self.voucher_repository.create(
                conn,
                standardized_code,
                voucher_type,
                value_decimal,
                min_purchase_decimal,
                max_uses_int,
            )
            conn.commit()
            new_voucher = self.voucher_repository.find_by_id(conn, new_id)
            return {
                "success": True,
                "message": f'Voucher "{standardized_code}" '
                           f'berhasil ditambahkan.',
                "data": new_voucher,
            }
        
        except ValueError:
            raise ValidationError(
                "Nilai, Minimal Belanja, atau Maks Penggunaan "
                "harus berupa angka yang valid."
            )
        
        except mysql.connector.IntegrityError:
            if conn and conn.is_connected():
                conn.rollback()
            return {
                "success": False,
                "message": f'Kode voucher "{standardized_code}" sudah terdaftar.',
            }
        
        except mysql.connector.Error as db_err:
            if conn and conn.is_connected():
                conn.rollback()
            raise DatabaseException(
                f"Kesalahan database saat menambahkan voucher: {db_err}"
            )
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            if isinstance(e, ValidationError):
                raise e
            raise ServiceLogicError(
                f"Gagal menambahkan voucher karena kesalahan server: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def delete_voucher_by_id(self, voucher_id: int) -> Dict[str, Any]:

        conn: Optional[MySQLConnection] = None

        try:
            conn = get_db_connection()
            conn.start_transaction()
            rowcount = self.voucher_repository.delete(conn, voucher_id)
            conn.commit()
            if rowcount > 0:
                return {
                    "success": True,
                    "message": "Voucher berhasil dihapus."
                }
            else:
                raise RecordNotFoundError("Voucher tidak ditemukan.")
            
        except mysql.connector.Error as db_err:
            if conn and conn.is_connected():
                conn.rollback()
            raise DatabaseException(
                f"Kesalahan database saat menghapus voucher: {db_err}"
            )
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            if isinstance(e, RecordNotFoundError):
                raise e
            raise ServiceLogicError(f"Gagal menghapus voucher: {e}")
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def toggle_voucher_status(self, voucher_id: int) -> Dict[str, Any]:

        conn: Optional[MySQLConnection] = None

        try:
            conn = get_db_connection()
            conn.start_transaction()
            voucher = self.voucher_repository.find_by_id(conn, voucher_id)
            if voucher:
                new_status = not voucher["is_active"]
                self.voucher_repository.toggle_status(
                    conn, voucher_id, new_status
                )
                conn.commit()
                status_text = "Aktif" if new_status else "Tidak Aktif"
                updated_voucher = self.voucher_repository.find_by_id(
                    conn, voucher_id
                )
                return {
                    "success": True,
                    "message": f"Status voucher berhasil diubah "
                               f"menjadi {status_text}.",
                    "data": updated_voucher,
                }
            else:
                conn.rollback()
                raise RecordNotFoundError("Voucher tidak ditemukan.")
            
        except mysql.connector.Error as db_err:
            if conn and conn.is_connected():
                conn.rollback()
            raise DatabaseException(
                f"Kesalahan database saat mengubah status voucher: {db_err}"
            )
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            if isinstance(e, RecordNotFoundError):
                raise e
            raise ServiceLogicError(f"Gagal mengubah status voucher: {e}")
        
        finally:
            if conn and conn.is_connected():
                conn.close()

voucher_service = VoucherService(voucher_repository)