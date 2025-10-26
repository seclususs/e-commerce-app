from decimal import Decimal
from typing import Any, Dict, List, Optional

import mysql.connector

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
        logger.debug(f"Mengambil voucher aktif berdasarkan kode: {code}")

        conn = None
        cursor = None
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "SELECT * FROM vouchers WHERE code = %s AND is_active = 1",
                (code,),
            )

            voucher = cursor.fetchone()

            if voucher:
                logger.info(f"Voucher aktif '{code}' ditemukan.")

            else:
                logger.info(f"Voucher aktif '{code}' tidak ditemukan.")

            return voucher
        
        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat mengambil voucher aktif '{code}': {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat mengambil voucher: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat mengambil voucher aktif '{code}': {e}",
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
                f"Koneksi database ditutup untuk get_active_voucher_by_code '{code}'."
            )


    def get_all_vouchers(self) -> List[Dict[str, Any]]:
        logger.debug("Mengambil semua data voucher dari service.")

        conn = None
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
        v_type: str,
        value: str,
        min_purchase: Optional[str],
        max_uses: Optional[str],
    ) -> Dict[str, Any]:
        upper_code = code.upper().strip()
        logger.debug(
            f"Service: Mencoba menambahkan voucher. Kode: {upper_code}, Tipe: {v_type}, "
            f"Nilai: {value}, Minimal Belanja: {min_purchase}, Maksimum Penggunaan: {max_uses}"
        )

        if not upper_code or not v_type or not value:
            logger.warning(
                "Service: Gagal menambahkan voucher: Kolom wajib belum diisi."
            )
            raise ValidationError("Kode, Tipe, dan Nilai tidak boleh kosong.")

        conn = None
        cursor = None

        try:
            value_decimal = Decimal(str(value))
            min_purchase_decimal = (
                Decimal(str(min_purchase))
                if min_purchase
                else Decimal("0")
            )
            max_uses_int = int(max_uses) if max_uses else None

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                """
                INSERT INTO vouchers (code, type, value, min_purchase_amount, max_uses)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    upper_code,
                    v_type,
                    value_decimal,
                    min_purchase_decimal,
                    max_uses_int,
                ),
            )

            new_id = cursor.lastrowid

            conn.commit()

            logger.info(
                f"Service: Voucher '{upper_code}' berhasil ditambahkan dengan ID: {new_id}"
            )

            cursor.execute("SELECT * FROM vouchers WHERE id = %s", (new_id,))

            new_voucher = cursor.fetchone()

            return {
                "success": True,
                "message": f'Voucher "{upper_code}" berhasil ditambahkan.',
                "data": new_voucher,
            }
        
        except ValueError:
            raise ValidationError(
                "Nilai, Minimal Belanja, atau Maks Penggunaan harus berupa angka yang valid."
            )
        
        except mysql.connector.IntegrityError:
            if conn and conn.is_connected():
                conn.rollback()
            logger.warning(
                f"Service: Gagal menambahkan voucher: kode '{upper_code}' sudah ada."
            )
            return {
                "success": False,
                "message": f'Kode voucher "{upper_code}" sudah terdaftar.',
            }
        
        except mysql.connector.Error as db_err:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan database saat menambahkan voucher '{upper_code}': {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat menambahkan voucher: {db_err}"
            )
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Service: Terjadi kesalahan saat menambahkan voucher '{upper_code}': {e}",
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
            logger.debug("Koneksi database ditutup untuk add_voucher.")


    def delete_voucher_by_id(self, voucher_id: int) -> Dict[str, Any]:
        logger.debug(
            f"Service: Mencoba menghapus voucher dengan ID: {voucher_id}"
        )

        conn = None
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
                return {"success": True, "message": "Voucher berhasil dihapus."}
            
            else:
                logger.warning(
                    f"Service: Voucher ID {voucher_id} tidak ditemukan saat akan dihapus."
                )
                raise RecordNotFoundError("Voucher tidak ditemukan.")
            
        except mysql.connector.Error as db_err:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan database saat menghapus voucher ID {voucher_id}: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat menghapus voucher: {db_err}"
            )
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Service: Terjadi kesalahan saat menghapus voucher ID {voucher_id}: {e}",
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

        conn = None
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
                    f"Service: Status voucher ID {voucher_id} berhasil diubah menjadi {status_text}."
                )

                cursor.execute(
                    "SELECT * FROM vouchers WHERE id = %s", (voucher_id,)
                )

                updated_voucher = cursor.fetchone()

                return {
                    "success": True,
                    "message": f"Status voucher berhasil diubah menjadi {status_text}.",
                    "data": updated_voucher,
                }
            
            else:
                logger.warning(
                    f"Service: Voucher ID {voucher_id} tidak ditemukan untuk diubah statusnya."
                )
                raise RecordNotFoundError("Voucher tidak ditemukan.")
            
        except mysql.connector.Error as db_err:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan database saat mengubah status voucher ID {voucher_id}: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat mengubah status voucher: {db_err}"
            )
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Service: Terjadi kesalahan saat mengubah status voucher ID {voucher_id}: {e}",
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