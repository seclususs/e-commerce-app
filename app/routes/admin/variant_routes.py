from typing import Any, Dict, List, Tuple, Union

from flask import (
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from app.core.db import get_content
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import (
    DatabaseException,
    RecordNotFoundError,
)
from app.exceptions.service_exceptions import ServiceLogicError
from app.services.products.product_query_service import product_query_service
from app.services.products.variant_service import variant_service
from app.utils.logging_utils import get_logger
from app.utils.route_decorators import admin_required

from . import admin_bp

logger = get_logger(__name__)


@admin_bp.route("/product/<int:product_id>/variants", methods=["GET", "POST"])
@admin_required
def manage_variants(
    product_id: int,
) -> Union[str, Response, Tuple[Response, int]]:
    if request.method == "POST":
        action: str = request.form.get("action")
        logger.debug(
            f"Permintaan POST untuk mengelola varian produk dengan ID: {product_id}. "
            f"Aksi: {action}. Data form: {request.form.to_dict()}"
        )
        
        result: Dict[str, Any] = {"success": False, "message": "Aksi tidak valid"}
        status_code: int = 400

        try:
            if action == "add":
                size: str = request.form.get("size")
                stock: str = request.form.get("stock")
                weight_grams: str = request.form.get("weight_grams")
                sku: str = request.form.get("sku")

                result = variant_service.add_variant(
                    product_id, size, stock, weight_grams, sku
                )

                if result.get("success"):
                    status_code = 200
                    html: str = render_template(
                        "admin/partials/_variant_row.html",
                        variant=result["data"],
                        product_id=product_id,
                    )
                    result["html"] = html
                    logger.info(
                        f"Varian '{size}' berhasil ditambahkan untuk "
                        f"produk ID {product_id}."
                    )

                else:
                    status_code = (
                        409 if "sudah ada" in result.get("message", "") else 400
                    )
                    logger.warning(
                        f"Gagal menambahkan varian untuk produk ID {product_id}. "
                        f"Alasan: {result.get('message')}"
                    )

            elif action == "update":
                variant_id: str = request.form.get("variant_id")
                size: str = request.form.get("size")
                stock: str = request.form.get("stock")
                weight_grams: str = request.form.get("weight_grams")
                sku: str = request.form.get("sku")

                result = variant_service.update_variant(
                    product_id, variant_id, size, stock, weight_grams, sku
                )

                if result.get("success"):
                    status_code = 200
                    result["data"] = dict(request.form)
                    logger.info(
                        f"Varian ID {variant_id} berhasil diperbarui "
                        f"untuk produk ID {product_id}."
                    )

                else:
                    status_code = (
                        409
                        if "sudah ada" in result.get("message", "")
                        else (
                            404
                            if "tidak ditemukan" in result.get("message", "")
                            else 400
                        )
                    )
                    logger.warning(
                        f"Gagal memperbarui varian ID {variant_id}. "
                        f"Alasan: {result.get('message')}"
                    )

            return jsonify(result), status_code

        except ValidationError as ve:
            logger.warning(
                f"Kesalahan validasi saat aksi varian '{action}' "
                f"untuk produk {product_id}: {ve}"
            )
            return jsonify({"success": False, "message": str(ve)}), 400
        
        except RecordNotFoundError as rnfe:
            logger.warning(
                f"Data Tidak Ditemukan saat aksi varian '{action}' "
                f"untuk produk {product_id}: {rnfe}"
            )
            return jsonify({"success": False, "message": str(rnfe)}), 404
        
        except DatabaseException as de:
            logger.error(
                f"Kesalahan Database saat aksi varian '{action}' "
                f"untuk produk {product_id}: {de}",
                exc_info=True,
            )
            return (
                jsonify(
                    {"success": False, "message": "Terjadi kesalahan database."}
                ),
                500,
            )
        
        except ServiceLogicError as sle:
            logger.error(
                f"Kesalahan Logika Servis saat aksi varian '{action}' "
                f"untuk produk {product_id}: {sle}",
                exc_info=True,
            )
            return (
                jsonify(
                    {"success": False, "message": "Terjadi kesalahan pada server."}
                ),
                500,
            )
        
        except Exception as e:
            logger.error(
                f"Terjadi kesalahan tak terduga saat memproses aksi "
                f"varian '{action}' untuk produk ID {product_id}: {e}",
                exc_info=True,
            )
            return (
                jsonify(
                    {"success": False, "message": "Terjadi kesalahan pada server."}
                ),
                500,
            )

    logger.debug(
        f"Permintaan GET untuk mengelola varian produk dengan ID: {product_id}"
    )

    try:
        product: Dict[str, Any] = product_query_service.get_product_by_id(
            product_id
        )

        if not product or not product["has_variants"]:
            logger.warning(
                f"Produk dengan ID {product_id} tidak ditemukan "
                f"atau tidak memiliki varian."
            )
            flash("Produk tidak ditemukan atau tidak memiliki varian.", "danger")
            return redirect(url_for("admin.admin_products"))

        variants: List[Dict[str, Any]] = (
            variant_service.get_variants_for_product(product_id)
        )
        logger.info(
            f"Berhasil mengambil {len(variants)} varian untuk "
            f"produk ID {product_id}."
        )

        return render_template(
            "admin/manage_variants.html",
            product=product,
            variants=variants,
            content=get_content(),
            product_id=product_id,
        )
    
    except (DatabaseException, ServiceLogicError) as service_err:
        logger.error(
            f"Kesalahan saat memuat halaman kelola varian "
            f"untuk produk {product_id}: {service_err}",
            exc_info=True,
        )
        flash("Gagal memuat halaman varian.", "danger")
        return redirect(url_for("admin.admin_products"))
    
    except Exception as e:
        logger.error(
            f"Terjadi kesalahan tak terduga saat memuat halaman "
            f"varian untuk produk ID {product_id}: {e}",
            exc_info=True,
        )
        flash("Gagal memuat halaman varian.", "danger")
        return redirect(url_for("admin.admin_products"))


@admin_bp.route(
    "/product/<int:product_id>/variant/delete/<int:variant_id>", methods=["POST"]
)
@admin_required
def delete_variant(product_id: int, variant_id: int) -> Tuple[Response, int]:
    logger.debug(
        f"Mencoba menghapus varian dengan ID {variant_id} "
        f"untuk produk ID {product_id}"
    )

    try:
        result: Dict[str, Any] = variant_service.delete_variant(
            product_id, variant_id
        )
        if result.get("success"):
            logger.info(f"Varian dengan ID {variant_id} berhasil dihapus.")
            return jsonify(result), 200
        else:
            logger.warning(
                f"Gagal menghapus varian dengan ID {variant_id}. "
                f"Alasan: {result.get('message')}"
            )
            status_code: int = (
                404 if "tidak ditemukan" in result.get("message", "") else 400
            )
            return jsonify(result), status_code

    except RecordNotFoundError as rnfe:
        logger.warning(
            f"Hapus gagal: Varian ID {variant_id} tidak ditemukan: {rnfe}"
        )
        return jsonify({"success": False, "message": str(rnfe)}), 404
    
    except DatabaseException as de:
        logger.error(
            f"Kesalahan Database saat menghapus varian ID {variant_id}: {de}",
            exc_info=True,
        )
        return (
            jsonify(
                {"success": False, "message": "Terjadi kesalahan database."}
            ),
            500,
        )
    
    except ServiceLogicError as sle:
        logger.error(
            f"Kesalahan Logika Servis saat menghapus varian ID {variant_id}: {sle}",
            exc_info=True,
        )
        return (
            jsonify(
                {"success": False, "message": "Terjadi kesalahan pada server."}
            ),
            500,
        )
    
    except Exception as e:
        logger.error(
            f"Terjadi kesalahan tak terduga saat menghapus "
            f"varian ID {variant_id}: {e}",
            exc_info=True,
        )
        return (
            jsonify(
                {"success": False, "message": "Terjadi kesalahan pada server."}
            ),
            500,
        )