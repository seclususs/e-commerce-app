from datetime import datetime
from decimal import Decimal
from typing import Any, Dict

import mysql.connector

from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.services.orders.voucher_service import voucher_service
from app.utils.logging_utils import get_logger


logger = get_logger(__name__)


class DiscountService:

    def validate_and_calculate_voucher(
        self, code: str, subtotal: float
    ) -> Dict[str, Any]:
        
        upper_code = code.upper()

        try:
            subtotal_decimal = Decimal(str(subtotal))

        except ValueError:
            raise ValidationError("Format subtotal tidak valid.")

        logger.debug(
            f"Memvalidasi kode voucher: {upper_code} "
            f"untuk subtotal: {subtotal_decimal}"
        )
        conn = None
        cursor = None

        try:
            voucher = voucher_service.get_active_voucher_by_code(upper_code)
            if not voucher:
                logger.info(
                    f"Validasi voucher gagal: Kode '{upper_code}' "
                    f"tidak ditemukan atau tidak aktif."
                )
                return {
                    "success": False,
                    "message": "Kode voucher tidak valid.",
                }
            
            logger.debug(f"Voucher '{upper_code}' ditemukan: {voucher}")
            now = datetime.now()

            if voucher["start_date"] and now < voucher["start_date"]:
                logger.info(
                    f"Validasi voucher '{upper_code}' gagal: Belum berlaku "
                    f"(dimulai {voucher['start_date']})."
                )
                return {"success": False, "message": "Voucher belum berlaku."}
            
            if voucher["end_date"] and now > voucher["end_date"]:
                logger.info(
                    f"Validasi voucher '{upper_code}' gagal: Kedaluwarsa "
                    f"(berakhir {voucher['end_date']})."
                )
                return {
                    "success": False,
                    "message": "Voucher sudah kedaluwarsa.",
                }
            
            if (
                voucher["max_uses"] is not None
                and voucher["use_count"] >= voucher["max_uses"]
            ):
                logger.info(
                    f"Validasi voucher '{upper_code}' gagal: Batas penggunaan "
                    f"({voucher['max_uses']}) tercapai."
                )
                return {
                    "success": False,
                    "message": "Voucher sudah habis digunakan.",
                }
            
            min_purchase_decimal = Decimal(
                str(voucher.get("min_purchase_amount", 0))
            )

            if subtotal_decimal < min_purchase_decimal:
                min_purchase_formatted = (
                    f"Rp {min_purchase_decimal:,.0f}".replace(",", ".")
                )
                logger.info(
                    f"Validasi voucher '{upper_code}' gagal: Subtotal {subtotal_decimal} "
                    f"kurang dari pembelian minimum {min_purchase_decimal}."
                )
                return {
                    "success": False,
                    "message": f"Minimal pembelian {min_purchase_formatted} "
                               f"untuk menggunakan voucher ini.",
                }
            
            discount_amount = Decimal("0")
            voucher_type = voucher["type"]
            voucher_value_decimal = Decimal(str(voucher["value"]))

            if voucher_type == "PERCENTAGE":
                discount_amount = (
                    voucher_value_decimal / Decimal("100")
                ) * subtotal_decimal
                discount_amount = discount_amount.quantize(Decimal("0.01"))
                logger.debug(
                    f"Menghitung diskon persentase untuk '{upper_code}': "
                    f"({voucher_value_decimal}% dari {subtotal_decimal}) = {discount_amount}"
                )

            elif voucher_type == "FIXED_AMOUNT":
                discount_amount = voucher_value_decimal
                logger.debug(
                    f"Menerapkan diskon jumlah tetap untuk '{upper_code}': {discount_amount}"
                )

            else:
                logger.error(
                    f"Tipe voucher '{voucher_type}' untuk kode '{upper_code}' tidak dikenal."
                )
                raise ValidationError(
                    f"Tipe voucher tidak dikenal: {voucher_type}"
                )
            
            discount_amount = min(discount_amount, subtotal_decimal)
            final_total = subtotal_decimal - discount_amount
            
            logger.info(
                f"Voucher '{upper_code}' berhasil divalidasi. "
                f"Diskon: {discount_amount}, Total Akhir: {final_total}"
            )
            return {
                "success": True,
                "discount_amount": float(discount_amount),
                "final_total": float(final_total),
                "message": "Voucher berhasil diterapkan!",
            }

        except (mysql.connector.Error, DatabaseException) as e:
            logger.error(
                f"Kesalahan database saat memvalidasi voucher '{upper_code}': {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat memvalidasi voucher: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat memvalidasi voucher '{upper_code}': {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Gagal memvalidasi voucher karena kesalahan server: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

discount_service = DiscountService()