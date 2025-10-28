from typing import Any, Dict, List, Tuple, Union

from flask import (
    Response, flash, jsonify, render_template, request
)

from app.core.db import get_content
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
)
from app.exceptions.service_exceptions import ServiceLogicError
from app.services.products.category_service import category_service
from app.utils.logging_utils import get_logger
from app.utils.route_decorators import admin_required

from . import admin_bp

logger = get_logger(__name__)


@admin_bp.route("/categories", methods=["GET", "POST"])
@admin_required
def admin_categories() -> Union[str, Response, Tuple[Response, int]]:
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    action = f"{request.method} /admin/categories (AJAX: {is_ajax})"
    logger.debug(f"Memulai {action}")

    if request.method == "POST":
        action_type: str = request.form.get("action")
        name: str = request.form.get("name")
        category_id: str = request.form.get("id")
        logger.debug(
            f"Menerima POST request. Action: {action_type}, "
            f"Name: {name}, ID: {category_id}"
        )

        result: Dict[str, Any] = {
            "success": False,
            "message": "Aksi tidak valid.",
        }
        status_code: int = 400

        try:
            if action_type == "add" and name:
                logger.info(f"Mencoba menambahkan kategori baru: {name}")
                result = category_service.create_category(name)

                if result.get("success"):
                    logger.info(f"Kategori '{name}' berhasil ditambahkan. ID: {result.get('data', {}).get('id')}")
                    html: str = render_template(
                        "partials/admin/_category_row.html",
                        category=result["data"],
                    )
                    result["html"] = html
                    status_code = 200
                else:
                    logger.warning(f"Gagal menambahkan kategori '{name}'. Pesan: {result.get('message')}")
                    if "sudah ada" in result.get("message", "").lower():
                        status_code = 409
                    else:
                        status_code = 400

            elif action_type == "edit" and name and category_id:
                logger.info(f"Mencoba mengedit kategori ID: {category_id} menjadi '{name}'")
                result = category_service.update_category(category_id, name)

                if result.get("success"):
                    logger.info(f"Kategori ID: {category_id} berhasil diupdate menjadi '{name}'")
                    result["data"] = {"id": category_id, "name": name}
                    status_code = 200
                else:
                    logger.warning(f"Gagal mengedit kategori ID: {category_id}. Pesan: {result.get('message')}")
                    if "sudah ada" in result.get("message", "").lower():
                        status_code = 409
                    elif "tidak ditemukan" in result.get("message", "").lower():
                        status_code = 404
                    else:
                        status_code = 400
            else:
                 logger.warning(f"Aksi POST tidak valid atau data kurang: Action: {action_type}, Name: {name}, ID: {category_id}")


            return jsonify(result), status_code

        except ValidationError as ve:
            logger.warning(f"Error validasi saat {action}: {ve}")
            return jsonify({"success": False, "message": str(ve)}), 400

        except RecordNotFoundError as rnfe:
            logger.warning(f"Record tidak ditemukan saat {action}: {rnfe}")
            return jsonify({"success": False, "message": str(rnfe)}), 404

        except DatabaseException as db_err:
            logger.error(f"Error database saat {action}: {db_err}", exc_info=True)
            return (
                jsonify(
                    {"success": False, "message": "Terjadi kesalahan database."}
                ),
                500,
            )

        except ServiceLogicError as service_err:
            logger.error(f"Error service saat {action}: {service_err}", exc_info=True)
            return (
                jsonify(
                    {"success": False, "message": "Terjadi kesalahan pada server."}
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
        
    page_title = "Manajemen Kategori - Admin"
    header_title = "Manajemen Kategori Produk"
    logger.debug("Menangani GET request untuk /admin/categories")

    try:
        logger.debug("Mencoba mengambil semua kategori dari service...")
        categories: List[Dict[str, Any]] = (
            category_service.get_all_categories()
        )
        logger.debug(f"Berhasil mengambil {len(categories)} kategori.")

        if is_ajax:
            logger.debug("Merender _manage_categories.html untuk respons AJAX")
            html = render_template(
                "partials/admin/_manage_categories.html",
                categories=categories,
                content=get_content(),
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
            logger.debug("Merender manage_categories.html untuk respons GET biasa")
            return render_template(
                "admin/manage_categories.html",
                categories=categories,
                content=get_content(),
            )

    except (DatabaseException, ServiceLogicError) as service_err:
        logger.error(
            f"Error service/DB saat GET /admin/categories: {service_err}",
            exc_info=True
            )
        message = "Gagal memuat daftar kategori."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        flash(message, "danger")
        return render_template(
            "admin/manage_categories.html",
            categories=[],
            content=get_content(),
        )

    except Exception as e:
        logger.exception(f"Error tidak terduga saat GET /admin/categories: {e}")
        message = "Terjadi kesalahan tidak terduga saat memuat halaman kategori."
        if is_ajax:
            return jsonify({"success": False, "message": "Gagal memuat daftar kategori."}), 500
        flash(message, "danger")
        return render_template(
            "admin/manage_categories.html",
            categories=[],
            content=get_content(),
        )


@admin_bp.route("/delete_category/<int:id>", methods=["POST"])
@admin_required
def delete_category(id: int) -> Tuple[Response, int]:
    action = f"POST /delete_category/{id}"
    logger.debug(f"Memulai {action}")
    try:
        logger.info(f"Mencoba menghapus kategori ID: {id}")
        result: Dict[str, Any] = category_service.delete_category(id)

        if result.get("success"):
            logger.info(f"Kategori ID: {id} berhasil dihapus.")
            return jsonify(result), 200

        else:
            logger.warning(f"Gagal menghapus kategori ID: {id}. Pesan: {result.get('message')}")
            status_code: int = (
                404 if "tidak ditemukan" in result.get("message", "").lower() else 400
            )
            return jsonify(result), status_code

    except RecordNotFoundError as rnfe:
        logger.warning(f"Record tidak ditemukan saat {action}: {rnfe}")
        return jsonify({"success": False, "message": str(rnfe)}), 404

    except DatabaseException as db_err:
            logger.error(f"Error database saat {action}: {db_err}", exc_info=True)
            return (
                jsonify(
                    {"success": False, "message": "Terjadi kesalahan database saat menghapus."}
                ),
                500,
            )

    except ServiceLogicError as service_err:
        logger.error(f"Error service saat {action}: {service_err}", exc_info=True)
        if "masih digunakan" in str(service_err).lower():
             return jsonify({"success": False, "message": str(service_err)}), 400
        else:
            return (
                jsonify(
                    {"success": False, "message": "Terjadi kesalahan pada server saat menghapus."}
                ),
                500,
            )

    except Exception as e:
        logger.exception(f"Error tidak terduga saat {action}: {e}")
        return (
            jsonify(
                {"success": False, "message": "Terjadi kesalahan tidak terduga pada server saat menghapus."}
            ),
            500,
        )