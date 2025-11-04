from typing import Any, Dict, Optional, Tuple

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.repository.product_repository import (
    ProductRepository, product_repository
)
from app.services.products.variant_service import VariantService, variant_service
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class VariantConversionService:

    def __init__(
        self,
        product_repo: ProductRepository = product_repository,
        variant_svc: VariantService = variant_service,
    ):
        self.product_repository = product_repo
        self.variant_service = variant_svc


    def convert_to_variant_product(
        self,
        product_id: Any,
        product_data: Dict[str, Any],
        conn: MySQLConnection,
    ) -> Tuple[int, int, Optional[str]]:
        
        logger.info(
            f"Mengonversi produk {product_id} menjadi produk varian."
        )

        try:
            initial_stock: int = (
                product_data.get("stock", 0)
                if product_data.get("stock", 0) > 0
                else 0
            )
            initial_weight: int = (
                product_data.get("weight_grams", 0)
                if product_data.get("weight_grams", 0) > 0
                else 0
            )
            initial_sku: Optional[str] = product_data.get("sku")
            add_result: Dict[str, Any] = self.variant_service.add_variant(
                product_id,
                "STANDAR",
                "STANDAR",
                initial_stock,
                initial_weight,
                initial_sku.upper() if initial_sku else None,
            )
            if not add_result["success"] and "sudah ada" not in add_result[
                "message"
            ]:
                logger.warning(
                    f"Gagal membuat varian awal untuk produk {product_id}: {add_result['message']}"
                )
                raise ServiceLogicError(
                    f"Gagal membuat varian awal: {add_result['message']}"
                )
            self.product_repository.update_stock_sku_weight_variant_status(
                conn, product_id, initial_stock, 0, None, True
            )
            logger.info(
                f"Produk {product_id} berhasil dikonversi ke tipe varian. Stok awal diatur ke {initial_stock}."
            )
            return initial_stock, 0, None
        
        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat konversi ke varian {product_id}: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat konversi ke varian: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat mengonversi produk {product_id} ke varian: {e}",
                exc_info=True,
            )
            if isinstance(e, TypeError):
                 raise ServiceLogicError(
                    f"Kesalahan layanan saat konversi ke varian: {e}"
                )
            raise ServiceLogicError(
                f"Kesalahan layanan saat konversi ke varian: {e}"
            )


    def convert_from_variant_product(
        self, product_id: Any, form_data: Any, conn: MySQLConnection
    ) -> Tuple[Any, Any, Any]:
        
        logger.info(
            f"Mengonversi produk {product_id} dari produk varian."
        )

        try:
            self.variant_service.delete_all_variants_for_product(
                product_id, conn
            )
            stock: Any = form_data.get("stock", 0)
            weight_grams: Any = form_data.get("weight_grams", 0)
            sku: Optional[str] = form_data.get("sku") or None
            sku_processed = sku.upper().strip() if sku else None

            self.product_repository.update_stock_sku_weight_variant_status(
                conn, product_id, stock, weight_grams, sku_processed, False
            )
            logger.info(
                f"Produk {product_id} dikonversi dari tipe varian. Stok: {stock}, Berat: {weight_grams}, SKU: {sku}"
            )
            return stock, weight_grams, sku

        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat konversi dari varian {product_id}: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat konversi dari varian: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat mengonversi produk {product_id} dari varian: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat konversi dari varian: {e}"
            )

variant_conversion_service = VariantConversionService(
    product_repository, variant_service
)