from typing import Any, Dict, Optional, Tuple

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.services.products.variant_service import variant_service
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class VariantConversionService:

    def convert_to_variant_product(
        self,
        product_id: Any,
        product_data: Dict[str, Any],
        conn: MySQLConnection
    ) -> Tuple[int, int, Optional[str]]:
        logger.info(
            f"Mengonversi produk {product_id} menjadi produk varian."
        )

        cursor: Optional[Any] = None

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
            add_result: Dict[str, Any] = variant_service.add_variant(
                product_id,
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
            
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE products SET stock = %s, weight_grams = 0, sku = NULL, has_variants = 1 WHERE id = %s",
                (initial_stock, product_id),
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
                exc_info=True
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat konversi ke varian: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()


    def convert_from_variant_product(
        self, product_id: Any, form_data: Any, conn: MySQLConnection
    ) -> Tuple[Any, Any, Any]:
        logger.info(
            f"Mengonversi produk {product_id} dari produk varian."
        )
        cursor: Optional[Any] = None

        try:
            variant_service.delete_all_variants_for_product(product_id, conn)
            stock: Any = form_data.get("stock", 0)
            weight_grams: Any = form_data.get("weight_grams", 0)
            sku: Optional[str] = form_data.get("sku") or None

            cursor = conn.cursor()

            cursor.execute(
                "UPDATE products SET stock = %s, weight_grams = %s, sku = %s, has_variants = 0 WHERE id = %s",
                (
                    stock,
                    weight_grams,
                    sku.upper().strip() if sku else None,
                    product_id
                ),
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
        
        finally:
            if cursor:
                cursor.close()

variant_conversion_service = VariantConversionService()