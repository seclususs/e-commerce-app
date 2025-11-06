from typing import Any, Dict, List, Tuple, Union

from flask import (
    Response, flash, jsonify, redirect,
    render_template, request, url_for
)

from app.core.db import get_content
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
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
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method == "POST":

        try:
            result: Dict[str, Any] = product_service.update_product(
                id, request.form, request.files
            )

            if result.get("success"):
                result["redirect_url"] = url_for("admin.admin_products")
                return jsonify(result), 200

            status_code: int = 400
            if "tidak ditemukan" in result.get("message", ""):
                status_code = 404
            elif "sudah ada" in result.get("message", ""):
                status_code = 409
            return jsonify(result), status_code

        except (ValidationError, FileOperationError) as user_error:
            return jsonify({"success": False, "message": str(user_error)}), 400

        except RecordNotFoundError as rnfe:
            return jsonify({"success": False, "message": str(rnfe)}), 404

        except DatabaseException:
            return (
                jsonify(
                    {"success": False, "message": "Terjadi kesalahan database."}
                ),
                500,
            )

        except ServiceLogicError:
            return (
                jsonify(
                    {"success": False, "message": "Terjadi kesalahan pada server."}
                ),
                500,
            )

        except Exception:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Terjadi kesalahan server saat memperbarui produk.",
                    }
                ),
                500,
            )

    try:
        product: Dict[str, Any] = product_query_service.get_product_by_id(id)

        if not product:
            message = "Produk tidak ditemukan."
            if is_ajax:
                return jsonify({"success": False, "message": message}), 404
            flash(message, "danger")
            return redirect(url_for("admin.admin_products"))

        categories: List[Dict[str, Any]] = (
            category_service.get_all_categories()
        )
        additional_images: List[str] = product.get(
            "additional_image_urls", []
        )

        variants: List[Dict[str, Any]] = product.get("variants", [])

        page_title = "Edit Produk - Admin"
        header_title = f"Edit Produk: {product.get('name', '')}"

        render_data = {
            "product": product,
            "additional_images": additional_images,
            "categories": categories,
            "variants": variants,
            "content": get_content(),
            "product_id": id
        }

        if is_ajax:
            html = render_template(
                "partials/admin/_product_editor.html",
                **render_data
            )
            return jsonify(
                {
                    "success": True,
                    "html": html,
                    "page_title": page_title,
                    "header_title": header_title,
                }
            )
        else:
            return render_template(
                "admin/product_editor.html",
                **render_data
            )

    except (DatabaseException, ServiceLogicError) as e:
        logger.error(
            f"Gagal memuat halaman edit produk {id}: {e}", 
            exc_info=True
            )
        message = "Gagal memuat detail produk."
        if is_ajax:
            return jsonify(
                {"success": False, "message": message}
                ), 500
        flash(message, "danger")
        return redirect(url_for("admin.admin_products"))

    except Exception as e:
        logger.error(
            f"Kesalahan tak terduga saat memuat edit produk {id}: {e}", 
            exc_info=True
            )
        message = "Gagal memuat detail produk."
        if is_ajax:
            return jsonify(
                {"success": False, "message": message}
                ), 500
        flash(message, "danger")
        return redirect(url_for("admin.admin_products"))


@admin_bp.route("/delete_product/<int:id>", methods=["POST"])
@admin_required
def delete_product(id: int) -> Tuple[Response, int]:

    try:
        result: Dict[str, Any] = product_service.delete_product(id)

        if result.get("success"):
            return jsonify(result), 200
        else:
            status_code: int = (
                404 if "tidak ditemukan" in result.get("message", "") else 400
            )
            return jsonify(result), status_code

    except RecordNotFoundError as rnfe:
        return jsonify({"success": False, "message": str(rnfe)}), 404

    except DatabaseException:
        return (
            jsonify(
                {"success": False, "message": "Terjadi kesalahan database."}
            ),
            500,
        )

    except ServiceLogicError:
        return (
            jsonify(
                {"success": False, "message": "Terjadi kesalahan pada server."}
            ),
            500,
        )

    except Exception:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Terjadi kesalahan server saat menghapus produk.",
                }
            ),
            500,
        )