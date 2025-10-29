import json
from typing import Any, Dict, List, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.core.db import get_db_connection
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.repository.product_repository import (
    ProductRepository, product_repository
)
from app.repository.variant_repository import (
    VariantRepository, variant_repository
)
from app.services.orders.stock_service import StockService, stock_service
from app.services.products.variant_service import (
    VariantService, variant_service
)
from app.utils.logging_utils import get_logger


logger = get_logger(__name__)


class ProductQueryService:

    def __init__(
        self,
        product_repo: ProductRepository = product_repository,
        variant_repo: VariantRepository = variant_repository,
        stock_svc: StockService = stock_service,
        variant_svc: VariantService = variant_service,
    ):
        self.product_repository = product_repo
        self.variant_repository = variant_repo
        self.stock_service = stock_svc
        self.variant_service = variant_svc


    def get_filtered_products(
        self, filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        
        logger.debug(f"Mengambil produk yang difilter dengan filter: {filters}")
        conn: Optional[MySQLConnection] = None
        
        try:
            conn = get_db_connection()
            products = self.product_repository.find_filtered(conn, filters)
            logger.info(
                f"Ditemukan {len(products)} produk yang cocok dengan filter."
            )
            return products
        
        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat memfilter produk: {e}", exc_info=True
            )
            raise DatabaseException(
                f"Kesalahan database saat memfilter produk: {e}"
            )
        
        except Exception as e:
            logger.error(f"Kesalahan saat memfilter produk: {e}", exc_info=True)
            raise ServiceLogicError(
                f"Kesalahan layanan saat memfilter produk: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                "Koneksi database ditutup untuk get_filtered_products"
            )


    def get_all_products_with_category(
        self,
        search: Optional[str] = None,
        category_id: Optional[Any] = None,
        stock_status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        
        logger.debug(
            f"Mengambil semua produk. Pencarian: {search}, "
            f"Kategori: {category_id}, Status Stok: {stock_status}"
        )
        conn: Optional[MySQLConnection] = None

        try:
            conn = get_db_connection()
            products = self.product_repository.find_all_with_category(
                conn, search, category_id, stock_status
            )
            logger.info(f"Ditemukan {len(products)} produk.")
            return products
        
        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat mengambil semua produk: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat mengambil produk: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat mengambil semua produk: {e}", exc_info=True
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat mengambil produk: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                "Koneksi database ditutup untuk get_all_products_with_category"
            )


    def get_product_by_id(self, product_id: Any) -> Optional[Dict[str, Any]]:

        logger.debug(f"Mengambil produk berdasarkan ID: {product_id}")
        conn: Optional[MySQLConnection] = None
        
        try:
            conn = get_db_connection()
            conn.start_transaction()
            product = self.product_repository.find_with_category(
                conn, product_id
            )
            if not product:
                logger.warning(f"ID Produk {product_id} tidak ditemukan.")
                conn.rollback()
                return None
            
            logger.debug(
                f"Meningkatkan popularitas untuk ID produk {product_id}"
            )
            self.product_repository.update_popularity(conn, product_id)
            conn.commit()
            try:
                product["additional_image_urls"] = (
                    json.loads(product["additional_image_urls"])
                    if product["additional_image_urls"]
                    else []
                )
            except (json.JSONDecodeError, TypeError) as json_err:
                logger.warning(
                    f"Gagal mem-parsing additional_image_urls untuk ID produk {product_id}: {json_err}",
                    exc_info=False,
                )
                product["additional_image_urls"] = []

            product["all_images"] = [product["image_url"]] + product[
                "additional_image_urls"
            ]
            product["variants"] = self.variant_service.get_variants_for_product(
                product_id, conn
            )
            logger.debug(
                f"Mengambil {len(product['variants'])} varian untuk ID produk {product_id}"
            )
            
            if product["has_variants"]:
                for variant in product["variants"]:
                    variant["stock"] = self.stock_service.get_available_stock(
                        product_id, variant["id"], conn
                    )
            else:
                product["stock"] = self.stock_service.get_available_stock(
                    product_id, None, conn
                )
            logger.info(f"Detail ID produk {product_id} berhasil diambil.")
            return product

        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat mengambil produk {product_id}: {e}",
                exc_info=True,
            )
            if conn.is_connected():
                conn.rollback()
            raise DatabaseException(
                f"Kesalahan database saat mengambil produk: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat mengambil ID produk {product_id}: {e}",
                exc_info=True,
            )
            if conn.is_connected():
                conn.rollback()
            raise ServiceLogicError(
                f"Kesalahan layanan saat mengambil produk: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk get_product_by_id {product_id}"
            )


    def get_related_products(
        self, product_id: Any, category_id: Any
    ) -> List[Dict[str, Any]]:
        
        logger.debug(
            f"Mengambil produk terkait untuk ID produk: {product_id}, ID kategori: {category_id}"
        )
        conn: Optional[MySQLConnection] = None

        try:
            conn = get_db_connection()
            related_products = self.product_repository.find_related(
                conn, product_id, category_id
            )
            logger.info(
                f"Ditemukan {len(related_products)} produk terkait untuk ID produk {product_id}"
            )
            return related_products
        
        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat mengambil produk terkait {product_id}: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat mengambil produk terkait: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat mengambil produk terkait untuk ID {product_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat mengambil produk terkait: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk get_related_products {product_id}"
            )

product_query_service = ProductQueryService(
    product_repository, variant_repository, stock_service, variant_service
)