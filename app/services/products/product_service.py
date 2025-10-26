from typing import Any, Dict, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.core.db import get_db_connection
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
    )
from app.exceptions.service_exceptions import ServiceLogicError
from app.services.products.image_service import image_service
from app.services.products.product_repository_service import (
    product_repository_service
    )
from app.services.products.variant_conversion_service import (
    variant_conversion_service
    )
from app.services.products.variant_service import variant_service
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ProductService:

    def create_product(
        self, form_data: Any, files: Any
    ) -> Dict[str, Any]:
        logger.debug(
            f"Service: Memulai pembuatan produk dengan data form: {list(form_data.keys())}"
        )

        conn: Optional[MySQLConnection] = None

        try:
            (
                main_image_url,
                additional_image_urls,
                _,
                _,
                image_error,
            ) = image_service.handle_image_upload(files, form_data)

            if image_error:
                logger.warning(
                    f"Service: Pembuatan produk gagal karena error gambar: {image_error}"
                )
                return {"success": False, "message": image_error}
            
            has_variants: bool = "has_variants" in form_data
            stock: Any = 0 if has_variants else form_data.get("stock", 10)
            weight_grams: Any = (
                0 if has_variants else form_data.get("weight_grams", 0)
            )
            sku: Optional[str] = form_data.get("sku") or None
            sku = sku.upper().strip() if sku else None
            if (
                not form_data.get("name")
                or not form_data.get("price")
                or not form_data.get("category_id")
                or not form_data.get("description")
            ):
                raise ValidationError(
                    "Nama, Harga, Kategori, dan Deskripsi wajib diisi."
                )
            
            product_data: Dict[str, Any] = {
                "name": form_data["name"],
                "price": form_data["price"],
                "discount_price": form_data.get("discount_price") or None,
                "description": form_data["description"],
                "category_id": form_data["category_id"],
                "colors": form_data.get("colors"),
                "image_url": main_image_url,
                "additional_image_urls": additional_image_urls,
                "stock": stock,
                "has_variants": has_variants,
                "weight_grams": weight_grams,
                "sku": sku,
            }

            conn = get_db_connection()
            conn.start_transaction()

            product_id: int = product_repository_service.create(
                product_data, conn
            )
            new_product_details: Dict[
                str, Any
            ] = product_repository_service.get_created_product_details(
                product_id, conn
            )

            conn.commit()

            logger.info(
                f"Service: Produk '{product_data['name']}' berhasil dibuat dengan ID: {product_id}"
            )

            return {
                "success": True,
                "message": "Produk berhasil ditambahkan!",
                "product": new_product_details,
            }

        except mysql.connector.IntegrityError as e:

            if conn and conn.is_connected():
                conn.rollback()

            current_sku: str = (form_data.get("sku") or "").upper().strip()
            if e.errno == 1062 and current_sku:
                logger.warning(
                    f"Service: Pembuatan produk gagal: SKU duplikat '{current_sku}'."
                )
                return {
                    "success": False,
                    "message": f'SKU "{current_sku}" sudah ada. Harap gunakan SKU yang unik.',
                }
            
            elif e.errno == 1062:
                logger.warning(
                    f"Service: Pembuatan produk gagal: Error entri duplikat (kemungkinan nama)."
                )
                return {
                    "success": False,
                    "message": f'Nama produk "{form_data["name"]}" mungkin sudah ada.',
                }
            
            logger.error(
                f"Service: Error integritas database saat pembuatan produk: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Terjadi kesalahan database integritas: {e}"
            )
        
        except ValidationError as ve:
            if conn and conn.is_connected():
                conn.rollback()
            logger.warning(
                f"Service: Gagal membuat produk karena validasi: {ve}"
            )
            return {"success": False, "message": str(ve)}
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Service: Error tak terduga saat pembuatan produk: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(f"Gagal menambahkan produk: {e}")
        
        finally:
            if conn and conn.is_connected():
                conn.close()
                logger.debug(
                    "Service: Koneksi database ditutup untuk create_product"
                )


    def update_product(
        self, product_id: Any, form_data: Any, files: Any
    ) -> Dict[str, Any]:
        logger.debug(f"Service: Memulai pembaruan produk ID: {product_id}")

        conn: Optional[MySQLConnection] = None
        sku: Optional[str] = None

        try:
            conn = get_db_connection()
            conn.start_transaction()

            product: Optional[
                Dict[str, Any]
            ] = product_repository_service.find_by_id(product_id, conn)

            if not product:
                logger.warning(
                    f"Service: Pembaruan produk gagal: Produk ID {product_id} tidak ditemukan."
                )
                raise RecordNotFoundError("Produk tidak ditemukan.")
            
            (
                final_main,
                final_additional,
                _,
                images_to_delete_marked,
                image_error,
            ) = image_service.handle_image_upload(files, form_data, product)

            if image_error:
                logger.warning(
                    f"Service: Pembaruan produk gagal untuk ID {product_id} karena error gambar: {image_error}"
                )
                raise ValidationError(image_error)
            
            old_has_variants: bool = product.get("has_variants", False)
            new_has_variants: bool = "has_variants" in form_data
            logger.debug(
                f"Service: Perubahan status varian: {old_has_variants} -> {new_has_variants}"
            )

            if (
                not form_data.get("name")
                or not form_data.get("price")
                or not form_data.get("category_id")
                or not form_data.get("description")
            ):
                raise ValidationError(
                    "Nama, Harga, Kategori, dan Deskripsi wajib diisi."
                )
            
            stock: Any = product.get("stock")
            weight_grams: Any = product.get("weight_grams")
            sku = product.get("sku")

            if not old_has_variants and new_has_variants:
                stock, weight_grams, sku = (
                    variant_conversion_service.convert_to_variant_product(
                        product_id, product, conn
                    )
                )

            elif old_has_variants and not new_has_variants:
                stock, weight_grams, sku = (
                    variant_conversion_service.convert_from_variant_product(
                        product_id, form_data, conn
                    )
                )

            else:
                if not new_has_variants:
                    stock = form_data.get("stock", product.get("stock"))
                    weight_grams = form_data.get(
                        "weight_grams", product.get("weight_grams")
                    )
                    sku_form: Optional[str] = form_data.get("sku") or None
                    sku = sku_form.upper().strip() if sku_form else None

            update_data: Dict[str, Any] = {
                "name": form_data["name"],
                "price": form_data["price"],
                "discount_price": form_data.get("discount_price") or None,
                "description": form_data["description"],
                "category_id": form_data["category_id"],
                "colors": form_data.get("colors"),
                "stock": stock,
                "image_url": final_main,
                "additional_image_urls": final_additional,
                "has_variants": new_has_variants,
                "weight_grams": weight_grams,
                "sku": sku,
            }
            update_successful: bool = product_repository_service.update(
                product_id, update_data, conn
            )

            if update_successful:
                conn.commit()

                if new_has_variants or (
                    old_has_variants and not new_has_variants
                ):
                    logger.debug(
                        f"Service: Memperbarui total stok dari varian untuk produk ID {product_id} setelah update."
                    )

                    update_conn_stock: Optional[MySQLConnection] = None

                    try:
                        update_conn_stock = get_db_connection()
                        variant_service.update_total_stock_from_variants(
                            product_id, update_conn_stock
                        )
                        update_conn_stock.commit()

                    except Exception as update_err:
                        logger.error(
                            f"Service: Error memperbarui total stok setelah konversi untuk {product_id}: {update_err}",
                            exc_info=True,
                        )

                        if (
                            update_conn_stock
                            and update_conn_stock.is_connected()
                        ):
                            update_conn_stock.rollback()

                    finally:
                        if (
                            update_conn_stock
                            and update_conn_stock.is_connected()
                        ):
                            update_conn_stock.close()

                logger.info(
                    f"Service: Produk ID {product_id} berhasil diperbarui."
                )

                return {
                    "success": True,
                    "message": "Produk berhasil diperbarui!"
                }
            
            else:
                conn.rollback()
                logger.warning(
                    f"Service: Tidak ada baris yang terpengaruh saat memperbarui produk ID {product_id}."
                )
                return {
                    "success": False,
                    "message": "Gagal memperbarui produk (tidak ada perubahan atau error).",
                }

        except mysql.connector.IntegrityError as e:
            if conn and conn.is_connected():
                conn.rollback()

            current_sku = form_data.get("sku") or sku
            current_sku = current_sku.upper().strip() if current_sku else None

            if e.errno == 1062 and current_sku:
                logger.warning(
                    f"Service: Pembaruan produk gagal untuk ID {product_id}: SKU duplikat '{current_sku}'."
                )
                return {
                    "success": False,
                    "message": "SKU yang dimasukkan sudah ada. Harap gunakan SKU yang unik.",
                }
            
            elif e.errno == 1062:
                logger.warning(
                    f"Service: Pembaruan produk gagal: Error entri duplikat (kemungkinan nama)."
                )
                return {
                    "success": False,
                    "message": f'Nama produk "{form_data["name"]}" mungkin sudah ada.',
                }
            
            logger.error(
                f"Service: Error integritas database saat pembaruan produk ID {product_id}: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Terjadi kesalahan database integritas: {e}"
            )
        
        except (ValidationError, RecordNotFoundError) as user_error:
            if conn and conn.is_connected():
                conn.rollback()
            logger.warning(
                f"Service: Gagal memperbarui produk {product_id}: {user_error}"
            )
            return {"success": False, "message": str(user_error)}
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Service: Error tak terduga saat pembaruan produk ID {product_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(f"Gagal memperbarui produk: {e}")
        
        finally:
            if conn and conn.is_connected():
                conn.close()
                logger.debug(
                    f"Service: Koneksi database ditutup untuk update_product {product_id}"
                )


    def delete_product(self, product_id: Any) -> Dict[str, Any]:
        logger.debug(f"Service: Memulai penghapusan produk ID: {product_id}")

        conn: Optional[MySQLConnection] = None

        try:
            conn = get_db_connection()
            conn.start_transaction()
            product: Optional[
                Dict[str, Any]
            ] = product_repository_service.find_by_id(product_id, conn)

            if not product:
                logger.warning(
                    f"Service: Penghapusan produk gagal: Produk ID {product_id} tidak ditemukan."
                )
                raise RecordNotFoundError("Produk tidak ditemukan.")
            
            logger.debug(
                f"Service: Menghapus varian untuk produk ID {product_id}"
            )

            variant_service.delete_all_variants_for_product(product_id, conn)
            logger.debug(
                f"Service: Menghapus produk ID {product_id} dari repository service"
            )

            deleted: bool = product_repository_service.delete(product_id, conn)

            if deleted:
                conn.commit()
                logger.info(
                    f"Service: Data produk untuk ID {product_id} berhasil dihapus."
                )
                logger.debug(
                    f"Service: Menghapus gambar untuk produk ID {product_id}"
                )
                image_service.delete_all_product_images(product)
                return {"success": True, "message": "Produk berhasil dihapus."}
            
            else:
                conn.rollback()
                logger.warning(
                    f"Service: Penghapusan produk ID {product_id} gagal di repository service."
                )
                raise RecordNotFoundError(
                    "Produk tidak ditemukan saat mencoba menghapus."
                )

        except RecordNotFoundError as rnfe:
            if conn and conn.is_connected():
                conn.rollback()
            return {"success": False, "message": str(rnfe)}
        
        except (mysql.connector.Error, DatabaseException) as db_err:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan database saat penghapusan produk {product_id}: {db_err}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat menghapus produk: {db_err}"
            )
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Service: Error saat penghapusan produk ID {product_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(f"Gagal menghapus produk: {e}")
        
        finally:
            if conn and conn.is_connected():
                conn.close()
                logger.debug(
                    f"Service: Koneksi database ditutup untuk delete_product {product_id}"
                )

product_service = ProductService()