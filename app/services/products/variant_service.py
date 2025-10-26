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


class VariantService:

    def get_variants_for_product(
        self, product_id: Any, conn: Optional[MySQLConnection] = None
    ) -> List[Dict[str, Any]]:
        logger.debug(f"Mengambil varian untuk ID produk: {product_id}")

        close_conn: bool = False
        cursor: Optional[Any] = None

        if conn is None:
            conn = get_db_connection()
            close_conn = True
            logger.debug(
                f"Membuat koneksi DB baru untuk get_variants_for_product {product_id}"
            )

        try:
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "SELECT * FROM product_variants WHERE product_id = %s ORDER BY id",
                (product_id,),
            )

            variants: List[Dict[str, Any]] = cursor.fetchall()

            logger.info(
                f"Mengambil {len(variants)} varian untuk ID produk: {product_id}"
            )

            return variants
        
        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat mengambil varian {product_id}: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat mengambil varian: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat mengambil varian untuk ID produk {product_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat mengambil varian: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()
            if close_conn and conn and conn.is_connected():
                conn.close()
                logger.debug(
                    f"Menutup koneksi DB untuk get_variants_for_product {product_id}"
                )


    def add_variant(
        self,
        product_id: Any,
        size: str,
        stock: Any,
        weight_grams: Any,
        sku: Optional[str]
    ) -> Dict[str, Any]:
        logger.debug(
            f"Mencoba menambahkan varian untuk ID produk: {product_id}. "
            f"Ukuran: {size}, Stok: {stock}, Berat: {weight_grams}, SKU: {sku}"
        )

        try:
            stock_int: int = int(stock)
            weight_int: int = int(weight_grams)

            if not size or not size.strip() or stock_int < 0 or weight_int < 0:
                raise ValidationError(
                    "Ukuran, stok (>=0), dan berat (>=0) harus diisi dengan benar."
                )
            
        except (ValueError, TypeError):
            raise ValidationError("Stok dan berat harus berupa angka.")

        conn: Optional[MySQLConnection] = None
        cursor: Optional[Any] = None
        new_id: Optional[int] = None
        upper_sku: Optional[str] = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            upper_sku = sku.upper().strip() if sku else None
            cursor.execute(
                """
                INSERT INTO product_variants (product_id, size, stock, weight_grams, sku)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    product_id,
                    size.upper().strip(),
                    stock_int,
                    weight_int,
                    upper_sku
                ),
            )

            new_id = cursor.lastrowid
            conn.commit()

            cursor.execute(
                "SELECT * FROM product_variants WHERE id = %s", (new_id,)
            )

            new_variant: Optional[Dict[str, Any]] = cursor.fetchone()

            logger.info(
                f"Varian '{size.upper()}' berhasil ditambahkan untuk ID produk {product_id}. "
                f"ID varian baru: {new_id}"
            )

            self.update_total_stock_from_variants(product_id, conn)

            return {
                "success": True,
                "message": f"Varian {size.upper()} berhasil ditambahkan.",
                "data": new_variant,
            }

        except mysql.connector.IntegrityError as e:
            if conn and conn.is_connected():
                conn.rollback()

            if e.errno == 1062:
                field: str = "SKU" if "sku" in str(e).lower() else "ukuran"
                value: Optional[str] = (
                    upper_sku if field == "SKU" else size.upper()
                )
                logger.warning(
                    f"Penambahan varian gagal: {field} duplikat '{value}' untuk ID produk {product_id}."
                )
                return {
                    "success": False,
                    "message": f'{field} "{value}" sudah ada untuk produk ini. Harap gunakan yang unik.',
                }
            
            logger.error(
                f"Kesalahan integritas database saat menambahkan varian untuk ID produk {product_id}: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                "Terjadi kesalahan database (Integrity) saat menambah varian."
            )

        except mysql.connector.Error as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan database saat menambahkan varian {product_id}: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat menambahkan varian: {e}"
            )
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan tak terduga saat menambahkan varian untuk ID produk {product_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(f"Gagal menambahkan varian: {e}")
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk add_variant {product_id}"
            )


    def update_variant(
        self,
        product_id: Any,
        variant_id: Any,
        size: str,
        stock: Any,
        weight_grams: Any,
        sku: Optional[str]
    ) -> Dict[str, Any]:
        logger.debug(
            f"Mencoba memperbarui ID varian: {variant_id} (Produk ID: {product_id}). "
            f"Ukuran: {size}, Stok: {stock}, Berat: {weight_grams}, SKU: {sku}"
        )

        try:
            stock_int: int = int(stock)
            weight_int: int = int(weight_grams)

            if not size or not size.strip() or stock_int < 0 or weight_int < 0:
                raise ValidationError(
                    "Ukuran, stok (>=0), dan berat (>=0) harus diisi dengan benar."
                )
            
        except (ValueError, TypeError):
            raise ValidationError("Stok dan berat harus berupa angka.")

        conn: Optional[MySQLConnection] = None
        cursor: Optional[Any] = None
        upper_sku: Optional[str] = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            upper_sku = sku.upper().strip() if sku else None

            cursor.execute(
                """
                UPDATE product_variants
                SET size = %s, stock = %s, weight_grams = %s, sku = %s
                WHERE id = %s AND product_id = %s
                """,
                (
                    size.upper().strip(),
                    stock_int,
                    weight_int,
                    upper_sku,
                    variant_id,
                    product_id,
                ),
            )

            if cursor.rowcount > 0:
                conn.commit()
                self.update_total_stock_from_variants(product_id, conn)
                logger.info(f"ID Varian {variant_id} berhasil diperbarui.")
                return {
                    "success": True,
                    "message": "Varian berhasil diperbarui."
                }
            
            else:
                conn.rollback()
                logger.warning(
                    f"Pembaruan varian gagal: ID Varian {variant_id} tidak ditemukan untuk produk ID {product_id}."
                )
                raise RecordNotFoundError(
                    "Varian tidak ditemukan atau tidak sesuai."
                )
            
        except mysql.connector.IntegrityError as e:
            if conn and conn.is_connected():
                conn.rollback()

            if e.errno == 1062:
                field: str = "SKU" if "sku" in str(e).lower() else "ukuran"
                value: Optional[str] = (
                    upper_sku if field == "SKU" else size.upper()
                )
                logger.warning(
                    f"Pembaruan varian gagal untuk ID {variant_id}: {field} duplikat '{value}'."
                )
                return {
                    "success": False,
                    "message": f'{field} "{value}" sudah ada untuk produk ini. Harap gunakan yang unik.',
                }
            
            logger.error(
                f"Kesalahan integritas database saat memperbarui ID varian {variant_id}: {e}",
                exc_info=True,
            )

            raise DatabaseException(
                "Terjadi kesalahan database (Integrity) saat memperbarui varian."
            )
        
        except mysql.connector.Error as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan database saat memperbarui varian {variant_id}: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat memperbarui varian: {e}"
            )
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan tak terduga saat memperbarui ID varian {variant_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(f"Gagal memperbarui varian: {e}")
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk update_variant {variant_id}"
            )


    def delete_variant(
        self, product_id: Any, variant_id: Any
    ) -> Dict[str, Any]:
        logger.debug(
            f"Mencoba menghapus ID varian: {variant_id} dari produk ID: {product_id}"
        )

        conn: Optional[MySQLConnection] = None
        cursor: Optional[Any] = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM product_variants WHERE id = %s AND product_id = %s",
                (variant_id, product_id),
            )

            if cursor.rowcount > 0:
                conn.commit()
                self.update_total_stock_from_variants(product_id, conn)
                logger.info(f"ID Varian {variant_id} berhasil dihapus.")
                return {"success": True, "message": "Varian berhasil dihapus."}
            
            else:
                conn.rollback()
                logger.warning(
                    f"Penghapusan varian gagal: ID Varian {variant_id} tidak ditemukan untuk produk ID {product_id}."
                )
                raise RecordNotFoundError(
                    "Varian tidak ditemukan atau tidak sesuai."
                )
            
        except mysql.connector.Error as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan database saat menghapus varian {variant_id}: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat menghapus varian: {e}"
            )
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan saat menghapus ID varian {variant_id}: {e}",
                exc_info=True
            )
            raise ServiceLogicError(f"Gagal menghapus varian: {e}")
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk delete_variant {variant_id}"
            )


    def delete_all_variants_for_product(
        self, product_id: Any, conn: MySQLConnection
    ) -> None:
        logger.debug(f"Menghapus semua varian untuk ID produk: {product_id}")
        cursor: Optional[Any] = None

        try:
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM product_variants WHERE product_id = %s",
                (product_id,)
            )

            deleted_count: int = cursor.rowcount
            logger.info(
                f"Menghapus {deleted_count} varian untuk ID produk {product_id}."
            )

        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat menghapus varian produk {product_id}: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat menghapus varian: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat menghapus semua varian untuk ID produk {product_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat menghapus varian: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()


    def update_total_stock_from_variants(
        self, product_id: Any, conn: Optional[MySQLConnection] = None
    ) -> bool:
        logger.debug(
            f"Memperbarui total stok dari varian untuk ID produk: {product_id}"
        )

        close_conn: bool = False
        cursor: Optional[Any] = None

        if conn is None:
            conn = get_db_connection()
            close_conn = True
            logger.debug(
                "Membuat koneksi DB baru untuk update_total_stock_from_variants."
            )

        try:
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "SELECT SUM(stock) AS total FROM product_variants WHERE product_id = %s",
                (product_id,),
            )

            total_stock_row: Optional[Dict[str, Any]] = cursor.fetchone()

            total_stock: int = (
                total_stock_row["total"]
                if total_stock_row and total_stock_row["total"] is not None
                else 0
            )

            cursor.execute(
                "UPDATE products SET stock = %s WHERE id = %s",
                (total_stock, product_id),
            )

            if close_conn:
                conn.commit()
                
            logger.info(
                f"Memperbarui total stok untuk ID produk {product_id} menjadi {total_stock}."
            )

            return True
        
        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat memperbarui stok total {product_id}: {e}",
                exc_info=True,
            )
            if close_conn and conn.is_connected():
                conn.rollback()
            raise DatabaseException(
                f"Kesalahan database saat memperbarui stok total: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat memperbarui total stok untuk ID produk {product_id}: {e}",
                exc_info=True,
            )
            if close_conn and conn.is_connected():
                conn.rollback()
            raise ServiceLogicError(
                f"Kesalahan layanan saat memperbarui stok total: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()
            if close_conn and conn and conn.is_connected():
                conn.close()
                logger.debug(
                    f"Koneksi database ditutup untuk update_total_stock_from_variants {product_id}"
                )

variant_service = VariantService()