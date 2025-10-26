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
from app.services.products.category_service import category_service
from app.utils.logging_utils import get_logger
from app.utils.route_decorators import admin_required

from . import admin_bp

logger = get_logger(__name__)


@admin_bp.route("/categories", methods=["GET", "POST"])
@admin_required
def admin_categories() -> Union[str, Response, Tuple[Response, int]]:

    if request.method == "POST":
        action: str = request.form.get("action")
        name: str = request.form.get("name")
        category_id: str = request.form.get("id")
        logger.debug(
            f"Permintaan POST ke /categories. Aksi: {action}, "
            f"Nama: {name}, ID: {category_id}"
        )
        result: Dict[str, Any] = {
            "success": False,
            "message": "Aksi tidak valid.",
        }
        status_code: int = 400

        try:
            if action == "add" and name:
                result = category_service.create_category(name)

                if result.get("success"):
                    html: str = render_template(
                        "admin/partials/_category_row.html",
                        category=result["data"],
                    )
                    result["html"] = html
                    status_code = 200
                    logger.info(
                        f"Kategori '{name}' berhasil ditambahkan via service. "
                        f"ID: {result['data']['id']}"
                    )

                else:
                    status_code = (
                        409 if "sudah ada" in result.get("message", "") else 400
                    )
                    logger.warning(
                        f"Gagal menambahkan kategori '{name}' via service. "
                        f"Alasan: {result.get('message')}"
                    )

            elif action == "edit" and name and category_id:
                result = category_service.update_category(category_id, name)

                if result.get("success"):
                    result["data"] = {"id": category_id, "name": name}
                    status_code = 200
                    logger.info(
                        f"Kategori dengan ID {category_id} "
                        f"berhasil diperbarui menjadi '{name}' via service."
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
                        f"Gagal memperbarui kategori ID {category_id} "
                        f"via service. Alasan: {result.get('message')}"
                    )

            return jsonify(result), status_code

        except ValidationError as ve:
            logger.warning(
                f"Kesalahan validasi saat aksi kategori '{action}': {ve}"
            )
            return jsonify({"success": False, "message": str(ve)}), 400

        except RecordNotFoundError as rnfe:
            logger.warning(
                f"Data tidak ditemukan saat aksi kategori '{action}': {rnfe}"
            )
            return jsonify({"success": False, "message": str(rnfe)}), 404

        except DatabaseException as de:
            logger.error(
                f"Kesalahan database saat aksi kategori '{action}': {de}",
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
                f"Kesalahan logika servis saat aksi kategori '{action}': {sle}",
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
                f"kategori '{action}': {e}",
                exc_info=True,
            )
            return (
                jsonify(
                    {"success": False, "message": "Terjadi kesalahan pada server."}
                ),
                500,
            )

    logger.debug("Permintaan GET ke /categories. Mengambil daftar kategori.")

    try:
        categories: List[Dict[str, Any]] = (
            category_service.get_all_categories()
        )
        logger.info(f"Berhasil mengambil {len(categories)} kategori.")
        return render_template(
            "admin/manage_categories.html",
            categories=categories,
            content=get_content(),
        )

    except (DatabaseException, ServiceLogicError) as service_err:
        logger.error(
            f"Kesalahan saat mengambil daftar kategori: {service_err}",
            exc_info=True,
        )
        flash("Gagal memuat daftar kategori.", "danger")
        return render_template(
            "admin/manage_categories.html",
            categories=[],
            content=get_content(),
        )

    except Exception as e:
        logger.error(
            f"Terjadi kesalahan tak terduga saat mengambil daftar kategori: {e}",
            exc_info=True,
        )
        flash("Gagal memuat daftar kategori.", "danger")
        return render_template(
            "admin/manage_categories.html",
            categories=[],
            content=get_content(),
        )


@admin_bp.route("/delete_category/<int:id>", methods=["POST"])
@admin_required
def delete_category(id: int) -> Tuple[Response, int]:
    logger.debug(f"Mencoba menghapus kategori dengan ID: {id}")

    try:
        result: Dict[str, Any] = category_service.delete_category(id)

        if result.get("success"):
            logger.info(
                f"Kategori dengan ID {id} berhasil dihapus via service."
            )
            return jsonify(result), 200
        
        else:
            logger.warning(
                f"Gagal menghapus kategori dengan ID {id} via service. "
                f"Alasan: {result.get('message')}"
            )
            status_code: int = (
                404 if "tidak ditemukan" in result.get("message", "") else 400
            )
            return jsonify(result), status_code

    except RecordNotFoundError as rnfe:
        logger.warning(f"Hapus gagal: Kategori ID {id} tidak ditemukan: {rnfe}")
        return jsonify({"success": False, "message": str(rnfe)}), 404

    except DatabaseException as de:
        logger.error(
            f"Kesalahan database saat menghapus kategori ID {id}: {de}",
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
            f"Kesalahan logika servis saat menghapus kategori ID {id}: {sle}",
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
            f"kategori dengan ID {id}: {e}",
            exc_info=True,
        )
        return (
            jsonify(
                {"success": False, "message": "Terjadi kesalahan pada server."}
            ),
            500,
        )