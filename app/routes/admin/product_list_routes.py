from typing import Any, Dict, List, Tuple, Union

from flask import (
    Response, flash, jsonify, render_template, request
)

from app.core.db import get_content
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.file_exceptions import FileOperationError
from app.exceptions.service_exceptions import ServiceLogicError
from app.services.products.category_service import category_service
from app.services.products.product_bulk_service import product_bulk_service
from app.services.products.product_query_service import product_query_service
from app.services.products.product_service import product_service
from app.utils.logging_utils import get_logger
from app.utils.route_decorators import admin_required

from . import admin_bp

logger = get_logger(__name__)


@admin_bp.route("/products", methods=["GET", "POST"])
@admin_required
def admin_products() -> Union[str, Response, Tuple[Response, int]]:
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    action = f"{request.method} /admin/products (AJAX: {is_ajax})"
    logger.debug(f"Memulai {action}")

    if request.method == "POST":
        form_type: str = request.form.get("form_type")
        logger.debug(f"Menerima POST request dengan form_type: {form_type}")

        try:
            if form_type == "bulk_action":
                action_bulk: str = request.form.get("bulk_action")
                selected_ids: List[str] = request.form.getlist("product_ids")
                category_id: str = request.form.get("bulk_category_id")
                logger.info(
                    f"Memproses bulk action: {action_bulk} "
                    f"untuk IDs: {selected_ids}, Kategori: {category_id}"
                )

                result: Dict[str, Any] = (
                    product_bulk_service.handle_bulk_product_action(
                        action_bulk, selected_ids, category_id
                    )
                )

                if result.get("success"):
                    logger.info(
                        f"Bulk action '{action_bulk}' berhasil. Data: {result}"
                    )
                    result["ids"] = selected_ids
                    result["action"] = action_bulk

                    if action_bulk == "set_category" and category_id:
                        category: Dict[str, Any] = (
                            category_service.get_category_by_id(int(category_id))
                        )
                        result["new_category_name"] = (
                            category["name"] if category else "Tidak diketahui"
                        )

                    return jsonify(result), 200

                logger.warning(
                    f"Bulk action '{action_bulk}' gagal. Pesan: {result.get('message')}"
                )
                return jsonify(result), 400

            elif form_type == "add_product":
                logger.info("Memproses penambahan produk baru.")
                result: Dict[str, Any] = product_service.create_product(
                    request.form, request.files
                )

                if result.get("success"):
                    product_data_from_service = result.get("product")
                    if product_data_from_service:
                        logger.info(
                            f"Produk baru {product_data_from_service.get('id')} "
                            f"ditemukan di respons service, merender HTML."
                        )
                        html = render_template(
                            "partials/admin/_product_row.html",
                            product=product_data_from_service,
                        )
                        return (
                            jsonify(
                                {
                                    "success": True,
                                    "message": result.get(
                                        "message", "Produk berhasil ditambahkan!"
                                    ),
                                    "html": html,
                                }
                            ),
                            200,
                        )
                    else:
                        logger.error(
                            f"Service create_product sukses, namun 'product' adalah None di response: {result}"
                            )
                        return (
                           jsonify(
                                {
                                    "success": False,
                                    "message": "Produk ditambahkan tapi gagal mengambil data untuk ditampilkan.",
                                }
                            ),
                            500,
                        )
                else:
                    logger.warning(
                        f"Gagal menambahkan produk baru. Pesan: {result.get('message')}"
                    )
                    status_code = 400
                    message = result.get("message", "")
                    if "sudah ada" in message:
                         status_code = 409
                    return jsonify(result), status_code

            else:
                logger.warning(f"Form type tidak dikenal: {form_type}")
                return (
                    jsonify(
                        {"success": False, "message": "Jenis form tidak dikenal."}
                    ),
                    400,
                )

        except ValidationError as ve:
            logger.warning(f"Error validasi saat {action}: {ve}")
            return jsonify({"success": False, "message": str(ve)}), 400

        except (DatabaseException, ServiceLogicError, FileOperationError) as service_err:
            logger.error(f"Error service/DB/File saat {action}: {service_err}", exc_info=True)
            return (
                jsonify(
                    {"success": False, "message": "Terjadi kesalahan pada server saat memproses permintaan."}
                ),
                500,
            )

        except Exception as e:
            logger.exception(f"Error tidak terduga saat {action}: {e}")
            return (
                jsonify(
                    {"success": False, "message": "Terjadi kesalahan tidak terduga pada server."}
                ),
                500,
            )

    search_term: str = request.args.get("search", "").strip()
    category_filter: str = request.args.get("category")
    stock_status_filter: str = request.args.get("stock_status")
    is_filter_request: str = request.args.get("is_filter_request") == "true"

    page_title = "Manajemen Produk - Admin"
    header_title = "Manajemen Produk"
    logger.debug(
        f"Mengambil daftar produk dengan filter - Search: '{search_term}'"
        f"Cat: {category_filter}"
        f"Stock: {stock_status_filter}"
        )

    try:
        logger.debug("Mencoba mengambil semua kategori...")
        categories: List[Dict[str, Any]] = (
            category_service.get_all_categories()
        )
        logger.debug(f"Berhasil mengambil {len(categories)} kategori.")

        logger.debug("Mencoba mengambil produk yang difilter...")
        products: List[Dict[str, Any]] = (
            product_query_service.get_all_products_with_category(
                search=search_term,
                category_id=category_filter,
                stock_status=stock_status_filter,
            )
        )
        logger.debug(f"Berhasil mengambil {len(products)} produk.")

        if is_ajax:
            if is_filter_request:
                logger.debug("Merender _product_table_body.html untuk respons AJAX filter")
                html: str = render_template(
                    "partials/admin/_product_table_body.html",
                    products=products,
                )
                return jsonify({"success": True, "html": html})
            else:
                logger.debug("Merender _manage_products.html untuk respons AJAX load awal")
                html: str = render_template(
                    "partials/admin/_manage_products.html",
                    products=products,
                    categories=categories,
                    content=get_content(),
                    search_term=search_term,
                )
                return jsonify(
                    {
                        "success": True,
                        "html": html,
                        "page_title": page_title,
                        "header_title": header_title,
                    }
                )

        logger.debug("Merender manage_products.html untuk respons GET biasa")
        return render_template(
            "admin/manage_products.html",
            products=products,
            categories=categories,
            content=get_content(),
            search_term=search_term,
        )

    except (DatabaseException, ServiceLogicError) as service_err:
        logger.error(
            f"Error service/DB saat GET /admin/products: {service_err}",
            exc_info=True
            )
        message = "Gagal memuat daftar produk atau kategori."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        flash(message, "danger")
        return render_template(
            "admin/manage_products.html",
            products=[],
            categories=[],
            content=get_content(),
            search_term=search_term,
        )

    except Exception as e:
        logger.exception(f"Error tidak terduga saat GET /admin/products: {e}")
        message = "Terjadi kesalahan tidak terduga saat memuat halaman produk."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        flash(message, "danger")
        return render_template(
            "admin/manage_products.html",
            products=[],
            categories=[],
            content=get_content(),
            search_term=search_term,
        )