import json
from typing import Any, Dict, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.core.db import get_db_connection
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
    )
from app.exceptions.service_exceptions import ServiceLogicError
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ProductRepositoryService:

    def find_by_id(
        self, product_id: Any, conn: Optional[MySQLConnection] = None
    ) -> Optional[Dict[str, Any]]:
        logger.debug(
            f"RepoService: Mencari produk berdasarkan ID: {product_id}"
        )

        close_conn: bool = False
        cursor: Optional[Any] = None

        if conn is None:
            conn = get_db_connection()
            close_conn = True

        try:
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT * FROM products WHERE id = %s", (product_id,))

            product: Optional[Dict[str, Any]] = cursor.fetchone()

            if product:

                try:
                    product["additional_image_urls"] = (
                        json.loads(product["additional_image_urls"])
                        if product["additional_image_urls"]
                        else []
                    )

                except (json.JSONDecodeError, TypeError):
                    product["additional_image_urls"] = []

            return product
        
        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat mencari produk ID {product_id}: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat mencari produk: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat mencari produk ID {product_id}: {e}",
                exc_info=True
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat mencari produk: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()
            if close_conn and conn and conn.is_connected():
                conn.close()


    def create(
        self, product_data: Dict[str, Any], conn: MySQLConnection
    ) -> int:
        logger.debug("RepoService: Membuat produk baru")
        cursor: Optional[Any] = None

        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO products (
                    name, price, discount_price, description, category_id, colors,
                    image_url, additional_image_urls, stock, has_variants,
                    weight_grams, sku
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    product_data["name"],
                    product_data["price"],
                    product_data.get("discount_price") or None,
                    product_data["description"],
                    product_data["category_id"],
                    product_data.get("colors"),
                    product_data["image_url"],
                    json.dumps(product_data["additional_image_urls"]),
                    product_data["stock"],
                    product_data["has_variants"],
                    product_data["weight_grams"],
                    product_data.get("sku"),
                ),
            )

            product_id: int = cursor.lastrowid

            return product_id
        
        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat membuat produk: {e}", exc_info=True
            )
            raise DatabaseException(
                f"Kesalahan database saat membuat produk: {e}"
            )
        
        except Exception as e:
            logger.error(f"Kesalahan saat membuat produk: {e}", exc_info=True)
            raise ServiceLogicError(
                f"Kesalahan layanan saat membuat produk: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()


    def get_created_product_details(
        self, product_id: int, conn: MySQLConnection
    ) -> Dict[str, Any]:
        cursor: Optional[Any] = None

        try:
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT p.*, c.name AS category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.id = %s
                """,
                (product_id,),
            )

            new_product_row: Optional[Dict[str, Any]] = cursor.fetchone()

            if not new_product_row:
                raise RecordNotFoundError(
                    f"Produk dengan ID {product_id} tidak ditemukan setelah dibuat."
                )
            
            return new_product_row
        
        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat mengambil detail produk {product_id}: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat mengambil detail produk: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat mengambil detail produk {product_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat mengambil detail produk: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()


    def update(
        self,
        product_id: Any,
        update_data: Dict[str, Any],
        conn: MySQLConnection
    ) -> int:
        logger.debug(f"RepoService: Memperbarui produk ID: {product_id}")
        cursor: Optional[Any] = None

        try:
            cursor = conn.cursor()
            additional_images_json = json.dumps(update_data.get("additional_image_urls", []))

            cursor.execute(
                """
                UPDATE products SET
                    name=%s, price=%s, discount_price=%s, description=%s, category_id=%s, colors=%s,
                    stock=%s, image_url=%s, additional_image_urls=%s, has_variants=%s,
                    weight_grams=%s, sku=%s
                WHERE id=%s
                """,
                (
                    update_data["name"],
                    update_data["price"],
                    update_data.get("discount_price") or None,
                    update_data["description"],
                    update_data["category_id"],
                    update_data.get("colors"),
                    update_data["stock"],
                    update_data["image_url"],
                    additional_images_json,
                    update_data["has_variants"],
                    update_data["weight_grams"],
                    update_data.get("sku"),
                    product_id,
                ),
            )

            affected_rows = cursor.rowcount
            logger.debug(f"RepoService: Baris terpengaruh oleh update: {affected_rows}")
            return affected_rows
        
        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat memperbarui produk {product_id}: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat memperbarui produk: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat memperbarui produk {product_id}: {e}",
                exc_info=True
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat memperbarui produk: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()


    def delete(self, product_id: Any, conn: MySQLConnection) -> bool:
        logger.debug(f"RepoService: Menghapus produk ID: {product_id}")

        cursor: Optional[Any] = None

        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
            return cursor.rowcount > 0
        
        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat menghapus produk {product_id}: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat menghapus produk: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat menghapus produk {product_id}: {e}",
                exc_info=True
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat menghapus produk: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()


    def update_popularity(
        self, product_id: Any, conn: MySQLConnection
    ) -> None:
        logger.debug(
            f"RepoService: Memperbarui popularitas produk ID: {product_id}"
        )

        cursor: Optional[Any] = None

        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE products SET popularity = popularity + 1 WHERE id = %s",
                (product_id,),
            )
            conn.commit()

        except mysql.connector.Error as e:
            if conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan database saat memperbarui popularitas produk ID {product_id}: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat memperbarui popularitas: {e}"
            )
        
        except Exception as e:
            if conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan saat memperbarui popularitas untuk ID produk {product_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat memperbarui popularitas: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()

product_repository_service = ProductRepositoryService()