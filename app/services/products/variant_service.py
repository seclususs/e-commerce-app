from typing import Any, Dict, List, Optional
from decimal import Decimal, InvalidOperation

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.core.db import get_db_connection
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
)
from app.exceptions.service_exceptions import ServiceLogicError
from app.repository.product_repository import (
    product_repository, ProductRepository
)
from app.repository.variant_repository import (
    variant_repository, VariantRepository
)


class VariantService:

    def __init__(
        self,
        variant_repo: VariantRepository = variant_repository,
        product_repo: ProductRepository = product_repository
    ):
        self.variant_repository = variant_repo
        self.product_repository = product_repo


    def get_variants_for_product(
        self, product_id: Any, conn: Optional[MySQLConnection] = None
    ) -> List[Dict[str, Any]]:

        close_conn: bool = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True

        try:
            return self.variant_repository.find_by_product_id(conn, product_id)

        except mysql.connector.Error as e:
            raise DatabaseException(
                f"Kesalahan database saat mengambil varian: {e}"
            )

        except Exception as e:
            raise ServiceLogicError(
                f"Kesalahan layanan saat mengambil varian: {e}"
            )

        finally:
            if close_conn and conn and conn.is_connected():
                conn.close()


    def _validate_variant_data(
        self,
        color: str,
        size: str,
        stock: Any,
        weight_grams: Any,
        price: Any,
        discount_price: Any
    ) -> Dict[str, Any]:
        
        try:
            stock_int: int = int(stock)
            weight_int: int = int(weight_grams)
            if (
                not color or not color.strip() or
                not size or not size.strip() or
                stock_int < 0 or weight_int < 0
            ):
                raise ValidationError(
                    "Warna, ukuran, stok (>=0), dan berat (>=0) "
                    "harus diisi dengan benar."
                )

            price_decimal: Optional[Decimal] = None
            if price:
                price_decimal = Decimal(str(price))
            
            discount_price_decimal: Optional[Decimal] = None
            if discount_price:
                discount_price_decimal = Decimal(str(discount_price))

            return {
                "color": color,
                "size": size,
                "stock_int": stock_int,
                "weight_int": weight_int,
                "price_decimal": price_decimal,
                "discount_price_decimal": discount_price_decimal
            }

        except (ValueError, TypeError, InvalidOperation):
            raise ValidationError(
                "Stok, berat, dan harga harus berupa angka yang valid."
                )


    def add_variant(
        self,
        product_id: Any,
        color: str,
        size: str,
        stock: Any,
        weight_grams: Any,
        price: Any,
        discount_price: Any,
        sku: Optional[str],
    ) -> Dict[str, Any]:

        validated_data = self._validate_variant_data(
            color, size, stock, weight_grams, price, discount_price
        )
        
        conn: Optional[MySQLConnection] = None
        upper_sku: Optional[str] = sku.upper().strip() if sku else None

        try:
            conn = get_db_connection()
            conn.start_transaction()
            new_id = self.variant_repository.create(
                conn, product_id,
                validated_data["color"],
                validated_data["size"],
                validated_data["stock_int"],
                validated_data["weight_int"],
                validated_data["price_decimal"],
                validated_data["discount_price_decimal"],
                upper_sku
            )
            self.update_total_stock_from_variants(product_id, conn)
            conn.commit()
            new_variant = self.variant_repository.find_by_id(conn, new_id)
            return {
                "success": True,
                "message": (
                    f"Varian {color.upper()} / {size.upper()} "
                    "berhasil ditambahkan."
                ),
                "data": new_variant,
            }

        except mysql.connector.IntegrityError as e:
            if conn and conn.is_connected():
                conn.rollback()
            if e.errno == 1062:
                field: str = "SKU"
                value: Optional[str] = upper_sku
                if "uk_product_color_size" in str(e).lower():
                    field = "Kombinasi Warna/Ukuran"
                    value = f"{color.upper()}/{size.upper()}"
                elif "sku" not in str(e).lower():
                    field = "Kombinasi Warna/Ukuran"
                    value = f"{color.upper()}/{size.upper()}"

                return {
                    "success": False,
                    "message": f'{field} "{value}" sudah ada untuk produk ini. '
                               f'Harap gunakan yang unik.',
                }
            raise DatabaseException(
                "Terjadi kesalahan database (Integrity) saat menambah varian."
            )

        except mysql.connector.Error as e:
            if conn and conn.is_connected():
                conn.rollback()
            raise DatabaseException(
                f"Kesalahan database saat menambahkan varian: {e}"
            )

        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            raise ServiceLogicError(f"Gagal menambahkan varian: {e}")

        finally:
            if conn and conn.is_connected():
                conn.close()


    def update_variant(
        self,
        product_id: Any,
        variant_id: Any,
        color: str,
        size: str,
        stock: Any,
        weight_grams: Any,
        price: Any,
        discount_price: Any,
        sku: Optional[str],
    ) -> Dict[str, Any]:

        validated_data = self._validate_variant_data(
            color, size, stock, weight_grams, price, discount_price
        )

        conn: Optional[MySQLConnection] = None
        upper_sku: Optional[str] = sku.upper().strip() if sku else None

        try:
            conn = get_db_connection()
            conn.start_transaction()
            rowcount = self.variant_repository.update(
                conn,
                variant_id,
                product_id,
                validated_data["color"],
                validated_data["size"],
                validated_data["stock_int"],
                validated_data["weight_int"],
                validated_data["price_decimal"],
                validated_data["discount_price_decimal"],
                upper_sku,
            )
            if rowcount > 0:
                self.update_total_stock_from_variants(product_id, conn)
                conn.commit()
                return {
                    "success": True,
                    "message": "Varian berhasil diperbarui."
                }
            else:
                conn.rollback()
                raise RecordNotFoundError(
                    "Varian tidak ditemukan atau tidak sesuai."
                )

        except mysql.connector.IntegrityError as e:
            if conn and conn.is_connected():
                conn.rollback()
            if e.errno == 1062:
                field: str = "SKU"
                value: Optional[str] = upper_sku
                if "uk_product_color_size" in str(e).lower():
                    field = "Kombinasi Warna/Ukuran"
                    value = f"{color.upper()}/{size.upper()}"
                elif "sku" not in str(e).lower():
                    field = "Kombinasi Warna/Ukuran"
                    value = f"{color.upper()}/{size.upper()}"

                return {
                    "success": False,
                    "message": f'{field} "{value}" sudah ada untuk produk ini. '
                               f'Harap gunakan yang unik.',
                }
            raise DatabaseException(
                "Terjadi kesalahan database (Integrity) "
                "saat memperbarui varian."
            )

        except mysql.connector.Error as e:
            if conn and conn.is_connected():
                conn.rollback()
            raise DatabaseException(
                f"Kesalahan database saat memperbarui varian: {e}"
            )

        except RecordNotFoundError as e:
            if conn and conn.is_connected():
                conn.rollback()
            raise e

        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            raise ServiceLogicError(f"Gagal memperbarui varian: {e}")

        finally:
            if conn and conn.is_connected():
                conn.close()


    def delete_variant(
        self, product_id: Any, variant_id: Any
    ) -> Dict[str, Any]:

        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            conn.start_transaction()

            rowcount = self.variant_repository.delete(
                conn, variant_id, product_id
            )

            if rowcount > 0:
                self.update_total_stock_from_variants(product_id, conn)
                conn.commit()
                return {"success": True, "message": "Varian berhasil dihapus."}
            else:
                conn.rollback()
                raise RecordNotFoundError(
                    "Varian tidak ditemukan atau tidak sesuai."
                )

        except mysql.connector.Error as e:
            if conn and conn.is_connected():
                conn.rollback()
            raise DatabaseException(
                f"Kesalahan database saat menghapus varian: {e}"
            )

        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            raise ServiceLogicError(f"Gagal menghapus varian: {e}")

        finally:
            if conn and conn.is_connected():
                conn.close()


    def delete_all_variants_for_product(
        self, product_id: Any, conn: MySQLConnection
    ) -> None:

        try:
            self.variant_repository.delete_by_product_id(conn, product_id)

        except mysql.connector.Error as e:
            raise DatabaseException(
                f"Kesalahan database saat menghapus varian: {e}"
            )

        except Exception as e:
            raise ServiceLogicError(
                f"Kesalahan layanan saat menghapus varian: {e}"
            )


    def update_total_stock_from_variants(
        self, product_id: Any, conn: Optional[MySQLConnection] = None
    ) -> bool:
        close_conn: bool = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True

        try:
            total_stock = self.variant_repository.get_total_stock(
                conn, product_id
            )
            self.product_repository.update_stock(
                conn, product_id, total_stock
            )
            if close_conn:
                conn.commit()
            return True

        except mysql.connector.Error as e:
            if close_conn and conn and conn.is_connected():
                conn.rollback()
            raise DatabaseException(
                f"Kesalahan database saat memperbarui stok total: {e}"
            )

        except Exception as e:
            if close_conn and conn and conn.is_connected():
                conn.rollback()
            raise ServiceLogicError(
                f"Kesalahan layanan saat memperbarui stok total: {e}"
            )

        finally:
            if close_conn and conn and conn.is_connected():
                conn.close()

variant_service = VariantService(variant_repository, product_repository)