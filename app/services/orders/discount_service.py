from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict

import mysql.connector

from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.services.orders.voucher_service import voucher_service
from app.utils.logging_utils import get_logger


logger = get_logger(__name__)


class DiscountService:

    def _validate_voucher_data(
        self, voucher: Dict[str, Any], subtotal: Decimal
    ) -> Dict[str, Any]:
        
        logger.debug(f"Memvalidasi data voucher: {voucher['code']}")
        now = datetime.now()

        if voucher.get("start_date") and now < voucher["start_date"]:
            return {"success": False, "message": "Voucher belum berlaku."}

        if voucher.get("end_date") and now > voucher["end_date"]:
            return {"success": False, "message": "Voucher sudah kedaluwarsa."}

        if (
            voucher.get("max_uses") is not None
            and voucher.get("use_count", 0) >= voucher["max_uses"]
        ):
            return {
                "success": False,
                "message": "Voucher sudah habis digunakan.",
            }

        min_purchase_decimal = Decimal(
            str(voucher.get("min_purchase_amount", 0))
        )
        if subtotal < min_purchase_decimal:
            min_purchase_formatted = (
                f"Rp {min_purchase_decimal:,.0f}".replace(",", ".")
            )
            return {
                "success": False,
                "message": (
                    f"Minimal pembelian {min_purchase_formatted} "
                    f"untuk menggunakan voucher ini."
                ),
            }

        discount_amount = Decimal("0")
        voucher_type = voucher["type"]
        voucher_value_decimal = Decimal(str(voucher["value"]))

        if voucher_type == "PERCENTAGE":
            discount_amount = (
                voucher_value_decimal / Decimal("100")
            ) * subtotal
            discount_amount = discount_amount.quantize(Decimal("0.01"))
        elif voucher_type == "FIXED_AMOUNT":
            discount_amount = voucher_value_decimal
        else:
            raise ValidationError(
                f"Tipe voucher tidak dikenal: {voucher_type}"
            )

        discount_amount = min(discount_amount, subtotal)
        final_total = subtotal - discount_amount
        return {
            "success": True,
            "discount_amount": float(discount_amount),
            "final_total": float(final_total),
            "message": "Voucher berhasil diterapkan!",
            "code": voucher["code"],
        }


    def validate_and_calculate_by_code(
        self, code: str, subtotal: float
    ) -> Dict[str, Any]:
        
        try:
            subtotal_decimal = Decimal(str(subtotal))

        except (ValueError, InvalidOperation) as e:
            logger.warning(
                f"Format subtotal tidak valid: {subtotal}. Error: {e}"
            )
            raise ValidationError("Format subtotal tidak valid.")

        logger.debug(
            f"Memvalidasi kode voucher: {code} "
            f"untuk subtotal: {subtotal_decimal}"
        )

        try:
            voucher = voucher_service.get_active_voucher_by_code(code)
            if not voucher:
                return {
                    "success": False,
                    "message": "Kode voucher tidak valid.",
                }

            result = self._validate_voucher_data(voucher, subtotal_decimal)
            return result

        except (mysql.connector.Error, DatabaseException) as e:
            logger.error(
                f"Kesalahan database saat memvalidasi voucher '{code}': {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat memvalidasi voucher: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat memvalidasi voucher '{code}': {e}",
                exc_info=True,
            )
            if isinstance(e, ValidationError):
                raise e
            raise ServiceLogicError(
                f"Gagal memvalidasi voucher karena kesalahan server: {e}"
            )


    def validate_and_calculate_by_id(
        self, user_id: int, user_voucher_id: int, subtotal: float
    ) -> Dict[str, Any]:
        
        try:
            subtotal_decimal = Decimal(str(subtotal))
        except (ValueError, InvalidOperation) as e:
            logger.warning(
                f"Format subtotal tidak valid: {subtotal}. Error: {e}"
            )
            raise ValidationError("Format subtotal tidak valid.")

        logger.debug(
            f"Memvalidasi user_voucher_id: {user_voucher_id} "
            f"untuk user: {user_id}"
        )
        try:
            voucher_data = voucher_service.get_user_voucher_by_id(
                user_id, user_voucher_id
            )
            if not voucher_data:
                return {
                    "success": False,
                    "message": "Voucher tidak ditemukan di akun Anda.",
                }
            if voucher_data["status"] != "available":
                return {
                    "success": False,
                    "message": "Voucher ini sudah Anda gunakan.",
                }

            result = self._validate_voucher_data(
                voucher_data, subtotal_decimal
            )
            if result["success"]:
                result["user_voucher_id"] = user_voucher_id
            return result

        except (mysql.connector.Error, DatabaseException) as e:
            logger.error(
                f"DB error validasi voucher by id '{user_voucher_id}': {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat memvalidasi voucher: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Error validasi voucher by id '{user_voucher_id}': {e}",
                exc_info=True,
            )
            if isinstance(e, ValidationError):
                raise e
            raise ServiceLogicError(
                f"Gagal memvalidasi voucher karena kesalahan server: {e}"
            )
        
discount_service = DiscountService()