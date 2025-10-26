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
from app.exceptions.file_exceptions import FileOperationError
from app.exceptions.service_exceptions import ServiceLogicError
from app.services.products.category_service import category_service
from app.services.products.product_query_service import product_query_service
from app.services.products.product_service import product_service
from app.utils.logging_utils import get_logger
from app.utils.route_decorators import admin_required

from . import admin_bp

logger = get_logger(__name__)


@admin_bp.route("/edit_product/<int:id>", methods=["GET", "POST"])
@admin_required
def admin_edit_product(id: int) -> Union[str, Response, Tuple[Response, int]]:
    if request.method == "POST":
        logger.debug(f"Mencoba memperbarui produk dengan ID: {id}")

        try:
            result: Dict[str, Any] = product_service.update_product(
                id, request.form, request.files
            )

            if result.get("success"):
                result["redirect_url"] = url_for("admin.admin_products")
                logger.info(f"Produk dengan ID {id} berhasil diperbarui.")
                return jsonify(result), 200

            logger.warning(
                f"Gagal memperbarui produk ID {id}. "
                f"Alasan: {result['message']}"
            )

            status_code: int = 400

            if "tidak ditemukan" in result.get("message", ""):
                status_code = 404
            elif "sudah ada" in result.get("message", ""):
                status_code = 409

            return jsonify(result), status_code

        except (ValidationError, FileOperationError) as user_error:
            logger.warning(
                f"Kesalahan Validasi/File saat memperbarui produk ID {id}: "
                f"{user_error}"
            )
            return jsonify({"success": False, "message": str(user_error)}), 400

        except RecordNotFoundError as rnfe:
            logger.warning(
                f"Pembaruan gagal: Produk ID {id} tidak ditemukan: {rnfe}"
            )
            return jsonify({"success": False, "message": str(rnfe)}), 404

        except DatabaseException as de:
            logger.error(
                f"Kesalahan database saat memperbarui produk ID {id}: {de}",
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
                f"Kesalahan logika servis saat memperbarui produk ID {id}: {sle}",
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
                f"Kesalahan tak terduga saat memperbarui produk ID {id}: {e}",
                exc_info=True,
            )
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Terjadi kesalahan server saat "
                        "memperbarui produk.",
                    }
                ),
                500,
            )

    logger.debug(f"Mengambil detail produk untuk diedit. ID Produk: {id}")

    try:
        product: Dict[str, Any] = product_query_service.get_product_by_id(id)

        if not product:
            logger.warning(
                f"Produk dengan ID {id} tidak ditemukan untuk diedit."
            )
            flash("Produk tidak ditemukan.", "danger")
            return redirect(url_for("admin.admin_products"))

        categories: List[Dict[str, Any]] = (
            category_service.get_all_categories()
        )
        additional_images: List[str] = product.get(
            "additional_image_urls", []
        )
        logger.info(
            f"Detail produk berhasil diambil untuk ID {id}. "
            f"Nama: {product.get('name')}"
        )
        return render_template(
            "admin/product_editor.html",
            product=product,
            additional_images=additional_images,
            categories=categories,
            content=get_content(),
        )

    except (DatabaseException, ServiceLogicError) as service_err:
        logger.error(
            f"Kesalahan saat memuat detail produk untuk edit ID {id}: "
            f"{service_err}",
            exc_info=True,
        )
        flash("Gagal memuat detail produk.", "danger")
        return redirect(url_for("admin.admin_products"))

    except Exception as e:
        logger.error(
            f"Kesalahan tak terduga saat mengambil detail produk ID {id}: {e}",
            exc_info=True,
        )
        flash("Gagal memuat detail produk.", "danger")
        return redirect(url_for("admin.admin_products"))


@admin_bp.route("/delete_product/<int:id>", methods=["POST"])
@admin_required
def delete_product(id: int) -> Tuple[Response, int]:
    logger.debug(f"Mencoba menghapus produk dengan ID: {id}")

    try:
        result: Dict[str, Any] = product_service.delete_product(id)

        if result.get("success"):
            logger.info(f"Produk dengan ID {id} berhasil dihapus.")
            return jsonify(result), 200
        
        else:
            logger.warning(
                f"Gagal menghapus produk ID {id}. "
                f"Alasan: {result.get('message')}"
            )
            status_code: int = (
                404 if "tidak ditemukan" in result.get("message", "") else 400
            )
            return jsonify(result), status_code

    except RecordNotFoundError as rnfe:
        logger.warning(f"Hapus gagal: Produk ID {id} tidak ditemukan: {rnfe}")
        return jsonify({"success": False, "message": str(rnfe)}), 404

    except DatabaseException as de:
        logger.error(
            f"Kesalahan database saat menghapus produk ID {id}: {de}",
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
            f"Kesalahan logika servis saat menghapus produk ID {id}: {sle}",
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
            f"Kesalahan tak terduga saat menghapus produk ID {id}: {e}",
            exc_info=True,
        )
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Terjadi kesalahan server saat menghapus produk.",
                }
            ),
            500,
        )