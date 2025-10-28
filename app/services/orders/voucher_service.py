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
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class VoucherService:
    
    def get_active_voucher_by_code(
        self, code: str
    ) -> Optional[Dict[str, Any]]:
        standardized_code = code.upper().strip()
        logger.debug(
            f"Mengambil voucher aktif berdasarkan kode (case-insensitive): "
            f"{standardized_code}"
        )
        conn: Optional[MySQLConnection] = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "SELECT * FROM vouchers WHERE UPPER(code) = %s "
                "AND is_active = 1",
                (standardized_code,),
            )

            voucher = cursor.fetchone()

            if voucher:
                logger.info(f"Voucher aktif '{standardized_code}' ditemukan.")
            else:
                logger.info(f"Voucher aktif '{standardized_code}' tidak ditemukan.")
            return voucher
        
        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat mengambil voucher aktif "
                f"'{standardized_code}': {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat mengambil voucher: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat mengambil voucher aktif "
                f"'{standardized_code}': {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat mengambil voucher: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk "
                f"get_active_voucher_by_code '{standardized_code}'."
            )


    def get_all_vouchers(self) -> List[Dict[str, Any]]:
        logger.debug("Mengambil semua data voucher dari service.")
        conn: Optional[MySQLConnection] = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM vouchers ORDER BY id DESC")
            vouchers = cursor.fetchall()
            logger.info(
                f"Berhasil mengambil {len(vouchers)} voucher dari service."
            )
            return vouchers
        
        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat mengambil semua voucher: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat mengambil voucher: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan service saat mengambil semua voucher: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat mengambil voucher: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug("Koneksi database ditutup untuk get_all_vouchers.")


    def add_voucher(
        self,
        code: str,
        voucher_type: str,
        value: str,
        min_purchase: Optional[str],
        max_uses: Optional[str],
    ) -> Dict[str, Any]:
        standardized_code = code.upper().strip()
        logger.debug(
            f"Service: Mencoba menambahkan voucher. Kode: {standardized_code}, "
            f"Tipe: {voucher_type}, Nilai: {value}, "
            f"Minimal Belanja: {min_purchase}, "
            f"Maksimum Penggunaan: {max_uses}"
        )

        if not standardized_code or not voucher_type or not value:
            logger.warning(
                "Service: Gagal menambahkan voucher: Kolom wajib belum diisi."
            )
            raise ValidationError("Kode, Tipe, dan Nilai tidak boleh kosong.")

        conn: Optional[MySQLConnection] = None
        cursor = None

        try:
            value_decimal = Decimal(str(value))
            min_purchase_decimal = (
                Decimal(str(min_purchase))
                if min_purchase
                else Decimal("0")
            )
            max_uses_int = int(max_uses) if max_uses else None

            if (voucher_type == "PERCENTAGE" and
                    not (0 <= value_decimal <= 100)):
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
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "SELECT id FROM vouchers WHERE UPPER(code) = %s",
                (standardized_code,)
            )
            existing_voucher = cursor.fetchone()
            if existing_voucher:
                logger.warning(
                    f"Service: Gagal menambahkan voucher: kode "
                    f"'{standardized_code}' sudah ada."
                )
                return {
                    "success": False,
                    "message": f'Kode voucher "{standardized_code}" sudah terdaftar.',
                }

            cursor.execute(
                """
                INSERT INTO vouchers
                (code, type, value, min_purchase_amount, max_uses)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    standardized_code,
                    voucher_type,
                    value_decimal,
                    min_purchase_decimal,
                    max_uses_int,
                ),
            )

            new_id = cursor.lastrowid

            conn.commit()

            logger.info(
                f"Service: Voucher '{standardized_code}' berhasil "
                f"ditambahkan dengan ID: {new_id}"
            )

            cursor.execute("SELECT * FROM vouchers WHERE id = %s", (new_id,))

            new_voucher = cursor.fetchone()

            return {
                "success": True,
                "message": f'Voucher "{standardized_code}" berhasil ditambahkan.',
                "data": new_voucher,
            }
        
        except ValueError:
            raise ValidationError(
                "Nilai, Minimal Belanja, atau Maks Penggunaan harus berupa "
                "angka yang valid."
            )
        
        except mysql.connector.IntegrityError:
            if conn and conn.is_connected():
                conn.rollback()
            logger.warning(
                f"Service: Gagal menambahkan voucher (IntegrityError despite "
                f"pre-check): kode '{standardized_code}' sudah ada."
            )
            return {
                "success": False,
                "message": f'Kode voucher "{standardized_code}" sudah terdaftar.',
            }
        
        except mysql.connector.Error as db_err:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan database saat menambahkan voucher "
                f"'{standardized_code}': {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat menambahkan voucher: {db_err}"
            )
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            if isinstance(e, ValidationError):
                raise e
            logger.error(
                f"Service: Terjadi kesalahan saat menambahkan voucher "
                f"'{standardized_code}': {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Gagal menambahkan voucher karena kesalahan server: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()


    def delete_voucher_by_id(self, voucher_id: int) -> Dict[str, Any]:
        logger.debug(
            f"Service: Mencoba menghapus voucher dengan ID: {voucher_id}"
        )

        conn: Optional[MySQLConnection] = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("DELETE FROM vouchers WHERE id = %s", (voucher_id,))

            conn.commit()

            if cursor.rowcount > 0:
                logger.info(
                    f"Service: Voucher ID {voucher_id} berhasil dihapus."
                )
                return {
                    "success": True,
                    "message": "Voucher berhasil dihapus."
                }
            
            else:
                logger.warning(
                    f"Service: Voucher ID {voucher_id} tidak ditemukan "
                    f"saat akan dihapus."
                )
                raise RecordNotFoundError("Voucher tidak ditemukan.")
            
        except mysql.connector.Error as db_err:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan database saat menghapus voucher ID {voucher_id}: "
                f"{db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat menghapus voucher: {db_err}"
            )
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            if isinstance(e, RecordNotFoundError):
                raise e
            logger.error(
                f"Service: Terjadi kesalahan saat menghapus voucher ID "
                f"{voucher_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(f"Gagal menghapus voucher: {e}")
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                "Koneksi database ditutup untuk delete_voucher_by_id."
            )


    def toggle_voucher_status(self, voucher_id: int) -> Dict[str, Any]:
        logger.debug(
            f"Service: Mencoba mengubah status voucher dengan ID: {voucher_id}"
        )

        conn: Optional[MySQLConnection] = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "SELECT is_active FROM vouchers WHERE id = %s FOR UPDATE",
                (voucher_id,),
            )

            voucher = cursor.fetchone()

            if voucher:
                new_status = not voucher["is_active"]

                cursor.execute(
                    "UPDATE vouchers SET is_active = %s WHERE id = %s",
                    (new_status, voucher_id),
                )

                conn.commit()

                status_text = "Aktif" if new_status else "Tidak Aktif"
                logger.info(
                    f"Service: Status voucher ID {voucher_id} berhasil "
                    f"diubah menjadi {status_text}."
                )

                cursor.execute(
                    "SELECT * FROM vouchers WHERE id = %s", (voucher_id,)
                )

                updated_voucher = cursor.fetchone()

                return {
                    "success": True,
                    "message": f"Status voucher berhasil diubah menjadi "
                               f"{status_text}.",
                    "data": updated_voucher,
                }
            
            else:
                conn.rollback()
                logger.warning(
                    f"Service: Voucher ID {voucher_id} tidak ditemukan "
                    f"untuk diubah statusnya."
                )
                raise RecordNotFoundError("Voucher tidak ditemukan.")
            
        except mysql.connector.Error as db_err:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan database saat mengubah status voucher ID "
                f"{voucher_id}: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat mengubah status voucher: {db_err}"
            )
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            if isinstance(e, RecordNotFoundError):
                raise e
            logger.error(
                f"Service: Terjadi kesalahan saat mengubah status voucher ID "
                f"{voucher_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(f"Gagal mengubah status voucher: {e}")
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                "Koneksi database ditutup untuk toggle_voucher_status."
            )

voucher_service = VoucherService()