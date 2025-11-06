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
    
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method == "POST":
        action: str = request.form.get("action")

        result: Dict[str, Any] = {"success": False, "message": "Aksi tidak valid"}
        status_code: int = 400

        try:
            if action == "add":
                color: str = request.form.get("color")
                size: str = request.form.get("size")
                stock: str = request.form.get("stock")
                weight_grams: str = request.form.get("weight_grams")
                price: str = request.form.get("price")
                discount_price: str = request.form.get("discount_price")
                sku: str = request.form.get("sku")
                result = variant_service.add_variant(
                    product_id, color, size, stock, weight_grams,
                    price, discount_price, sku
                )

                if result.get("success"):
                    status_code = 200
                    product = product_query_service.get_product_by_id(
                        product_id
                    )
                    html: str = render_template(
                        "partials/admin/_variant_row.html",
                        variant=result["data"],
                        product_id=product_id,
                        product=product,
                    )
                    result["html"] = html
                else:
                    status_code = (
                        409
                        if "sudah ada" in result.get("message", "")
                        else 400
                    )

            elif action == "update":
                variant_id: str = request.form.get("variant_id")
                color: str = request.form.get("color")
                size: str = request.form.get("size")
                stock: str = request.form.get("stock")
                weight_grams: str = request.form.get("weight_grams")
                price: str = request.form.get("price")
                discount_price: str = request.form.get("discount_price")
                sku: str = request.form.get("sku")
                result = variant_service.update_variant(
                    product_id, variant_id, color, size,
                    stock, weight_grams, price, discount_price, sku
                )

                if result.get("success"):
                    status_code = 200
                    result["data"] = dict(request.form)
                else:
                    if "sudah ada" in result.get("message", ""):
                        status_code = 409
                    elif "tidak ditemukan" in result.get("message", ""):
                        status_code = 404
                    else:
                        status_code = 400

            return jsonify(result), status_code

        except ValidationError as ve:
            return jsonify({"success": False, "message": str(ve)}), 400

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
                    {"success": False, "message": "Terjadi kesalahan pada server."}
                ),
                500,
            )

    try:
        product: Dict[str, Any] = product_query_service.get_product_by_id(
            product_id
        )

        if not product or not product.get("has_variants"):
            message = "Produk tidak ditemukan atau tidak memiliki varian."
            if is_ajax:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": message,
                            "redirect_url": url_for(
                                "admin.admin_edit_product", id=product_id
                            ),
                        }
                    ),
                    404,
                )
            flash(message, "danger")
            return redirect(url_for("admin.admin_edit_product", id=product_id))

        variants: List[Dict[str, Any]] = (
            variant_service.get_variants_for_product(product_id)
        )
        page_title = f"Kelola Varian - {product.get('name', '')} - Admin"
        header_title = f"Kelola Varian untuk: {product.get('name', '')}"

        if is_ajax:
            html = render_template(
                "partials/admin/_manage_variants_content.html",
                product=product,
                variants=variants,
                content=get_content(),
                product_id=product_id,
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
            flash(
                "Halaman ini telah dipindahkan. Gunakan tab 'Varian Produk' "
                "di halaman Edit Produk.", "info"
            )
            return redirect(url_for("admin.admin_edit_product", id=product_id))

    except (DatabaseException, ServiceLogicError):
        message = "Gagal memuat halaman varian."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        flash(message, "danger")
        return redirect(url_for("admin.admin_edit_product", id=product_id))

    except Exception:
        message = "Gagal memuat halaman varian."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        flash(message, "danger")
        return redirect(url_for("admin.admin_edit_product", id=product_id))


@admin_bp.route(
    "/product/<int:product_id>/variant/delete/<int:variant_id>", methods=["POST"]
)
@admin_required
def delete_variant(product_id: int, variant_id: int) -> Tuple[Response, int]:

    try:
        result: Dict[str, Any] = variant_service.delete_variant(
            product_id, variant_id
        )
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
                {"success": False, "message": "Terjadi kesalahan pada server."}
            ),
            500,
        )