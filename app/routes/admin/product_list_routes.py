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
    if request.method == "POST":
        form_type: str = request.form.get("form_type")
        logger.debug(f"Permintaan POST ke /products. Jenis form: {form_type}")

        try:
            if form_type == "bulk_action":
                action: str = request.form.get("bulk_action")
                selected_ids: List[str] = request.form.getlist("product_ids")
                category_id: str = request.form.get("bulk_category_id")
                logger.info(
                    f"Menjalankan aksi massal: {action} pada produk "
                    f"dengan ID: {selected_ids}. Kategori ID: {category_id}"
                )
                result: Dict[str, Any] = (
                    product_bulk_service.handle_bulk_product_action(
                        action, selected_ids, category_id
                    )
                )

                if result.get("success"):
                    result["ids"] = selected_ids
                    result["action"] = action

                    if action == "set_category" and category_id:
                        category: Dict[str, Any] = (
                            category_service.get_category_by_id(category_id)
                        )
                        result["new_category_name"] = (
                            category["name"] if category else "Tidak diketahui"
                        )
                    logger.info(
                        f"Aksi massal '{action}' berhasil dijalankan. "
                        f"Pesan: {result['message']}"
                    )
                    return jsonify(result), 200
                
                logger.warning(
                    f"Aksi massal '{action}' gagal dijalankan. "
                    f"Alasan: {result.get('message')}"
                )

                return jsonify(result), 400

            if form_type == "add_product":
                logger.info("Menambahkan produk baru.")
                result: Dict[str, Any] = product_service.create_product(
                    request.form, request.files
                )

                if result.get("success"):
                    flash(
                        result.get("message", "Produk berhasil ditambahkan!"),
                        "success",
                    )
                    logger.info(
                        f"Produk '{request.form.get('name')}' "
                        f"berhasil ditambahkan."
                    )

                else:
                    flash(
                        result.get("message", "Gagal menambahkan produk."),
                        "danger",
                    )
                    logger.warning(
                        f"Gagal menambahkan produk "
                        f"'{request.form.get('name')}'. "
                        f"Alasan: {result.get('message')}"
                    )

                return redirect(url_for("admin.admin_products"))

            logger.warning(
                f"Jenis form tidak dikenal dikirimkan: {form_type}"
            )
            flash("Jenis form tidak dikenal.", "danger")

            return redirect(url_for("admin.admin_products"))

        except ValidationError as ve:
            logger.warning(
                f"Kesalahan validasi saat memproses permintaan POST "
                f"untuk form_type '{form_type}': {ve}"
            )
            if form_type == "bulk_action":
                return jsonify({"success": False, "message": str(ve)}), 400
            flash(str(ve), "danger")
            return redirect(url_for("admin.admin_products"))

        except (
            DatabaseException,
            ServiceLogicError,
            FileOperationError,
        ) as service_err:
            logger.error(
                f"Kesalahan Service/DB/File saat memproses permintaan POST "
                f"untuk form_type '{form_type}': {service_err}",
                exc_info=True,
            )
            if form_type == "bulk_action":
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Terjadi kesalahan pada server.",
                        }
                    ),
                    500,
                )
            flash(
                "Terjadi kesalahan server saat memproses permintaan.", "danger"
            )
            return redirect(url_for("admin.admin_products"))

        except Exception as e:
            logger.error(
                f"Kesalahan tak terduga saat memproses permintaan POST "
                f"untuk form_type '{form_type}': {e}",
                exc_info=True,
            )
            if form_type == "bulk_action":
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Terjadi kesalahan pada server.",
                        }
                    ),
                    500,
                )
            flash(
                "Terjadi kesalahan server saat memproses permintaan.", "danger"
            )
            return redirect(url_for("admin.admin_products"))

    search_term: str = request.args.get("search", "").strip()
    category_filter: str = request.args.get("category")
    stock_status_filter: str = request.args.get("stock_status")
    logger.debug(
        f"Mengambil daftar produk dengan filter - Pencarian: {search_term}, "
        f"Kategori: {category_filter}, Status Stok: {stock_status_filter}"
    )

    try:
        products: List[Dict[str, Any]] = (
            product_query_service.get_all_products_with_category(
                search=search_term,
                category_id=category_filter,
                stock_status=stock_status_filter,
            )
        )
        logger.info(
            f"Berhasil mengambil {len(products)} produk sesuai filter."
        )

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            logger.debug(
                "Mengembalikan respon JSON untuk "
                "permintaan filter produk AJAX."
            )
            html: str = render_template(
                "admin/partials/_product_table_body.html", products=products
            )
            return jsonify({"success": True, "html": html})
        
        categories: List[Dict[str, Any]] = (
            category_service.get_all_categories()
        )
        logger.info("Menampilkan halaman kelola produk.")
        
        return render_template(
            "admin/manage_products.html",
            products=products,
            categories=categories,
            content=get_content(),
            search_term=search_term,
        )

    except (DatabaseException, ServiceLogicError) as service_err:
        logger.error(
            f"Kesalahan saat mengambil data produk atau kategori: {service_err}",
            exc_info=True,
        )
        flash("Gagal memuat daftar produk atau kategori.", "danger")
        return render_template(
            "admin/manage_products.html",
            products=[],
            categories=[],
            content=get_content(),
            search_term=search_term,
        )

    except Exception as e:
        logger.error(
            f"Kesalahan tak terduga saat mengambil data produk atau kategori: {e}",
            exc_info=True,
        )
        flash("Gagal memuat daftar produk atau kategori.", "danger")
        return render_template(
            "admin/manage_products.html",
            products=[],
            categories=[],
            content=get_content(),
            search_term=search_term,
        )