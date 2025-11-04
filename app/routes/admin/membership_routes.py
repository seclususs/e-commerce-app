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
from app.services.member.membership_service import membership_service
from app.utils.logging_utils import get_logger
from app.utils.route_decorators import admin_required

from . import admin_bp

logger = get_logger(__name__)


@admin_bp.route("/memberships", methods=["GET", "POST"])
@admin_required
def admin_memberships() -> Union[str, Response, Tuple[Response, int]]:
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    action = f"{request.method} /admin/memberships (AJAX: {is_ajax})"
    logger.debug(f"Memulai {action}")

    if request.method == "POST":
        action_type: str = request.form.get("action")
        form_data: Dict[str, Any] = request.form.to_dict()
        
        result: Dict[str, Any] = {
            "success": False, "message": "Aksi tidak valid."
        }
        status_code: int = 400

        try:
            if action_type == "add":
                logger.info("Mencoba menambahkan paket membership baru.")
                result = membership_service.create_membership(form_data)
                if result.get("success"):
                    status_code = 200
                    html: str = render_template(
                        "partials/admin/_membership_row.html",
                        membership=result["data"]
                    )
                    result["html"] = html
                else:
                    status_code = 400

            elif action_type == "update":
                membership_id = int(request.form.get("membership_id"))
                logger.info(
                    f"Mencoba memperbarui paket membership ID: {membership_id}"
                    )
                result = membership_service.update_membership(
                    membership_id, form_data
                )
                if result.get("success"):
                    status_code = 200
                    result["data"] = result["data"]
                else:
                    status_code = (
                        404 if "tidak ditemukan" in result.get("message", "")
                        else 400
                    )
            
            return jsonify(result), status_code

        except (ValidationError, RecordNotFoundError) as e:
            logger.warning(
                f"Error validasi/data saat {action}: {e}"
                )
            return (
                jsonify({"success": False, "message": str(e)}),
                404 if isinstance(e, RecordNotFoundError) else 400
            )
        
        except (DatabaseException, ServiceLogicError) as e:
            logger.error(
                f"Error service/DB saat {action}: {e}", 
                exc_info=True
                )
            return (
                jsonify(
                    {"success": False, "message": "Kesalahan server."}
                    ), 500
            )
        
        except Exception as e:
            logger.error(
                f"Error tak terduga saat {action}: {e}", 
                exc_info=True
                )
            return (
                jsonify(
                    {"success": False, "message": "Kesalahan tak terduga."}
                    ), 500
            )

    page_title = "Manajemen Membership - Admin"
    header_title = "Manajemen Paket Membership"
    logger.debug("Menangani GET request untuk /admin/memberships")

    try:
        memberships: List[Dict[str, Any]] = (
            membership_service.get_all_memberships_for_admin()
        )
        logger.debug(
            f"Berhasil mengambil {len(memberships)} paket membership."
            )
        if is_ajax:
            html = render_template(
                "partials/admin/_manage_memberships.html",
                memberships=memberships,
                content=get_content(),
            )
            return jsonify({
                "success": True,
                "html": html,
                "page_title": page_title,
                "header_title": header_title,
            })
        else:
            return render_template(
                "admin/manage_memberships.html",
                memberships=memberships,
                content=get_content(),
            )

    except (DatabaseException, ServiceLogicError) as e:
        logger.error(
            f"Error service/DB saat GET /admin/memberships: {e}", 
            exc_info=True
        )
        message = "Gagal memuat daftar paket membership."
        if is_ajax:
            return jsonify(
                {"success": False, "message": message}
                ), 500
        flash(message, "danger")
        return render_template(
            "admin/manage_memberships.html",
            memberships=[],
            content=get_content()
        )


@admin_bp.route("/memberships/delete/<int:id>", methods=["POST"])
@admin_required
def delete_membership(id: int) -> Tuple[Response, int]:
    action = f"POST /memberships/delete/{id}"
    logger.debug(f"Memulai {action}")
    try:
        result: Dict[str, Any] = membership_service.delete_membership(id)
        if result.get("success"):
            logger.info(f"Paket membership ID: {id} berhasil dihapus.")
            return jsonify(result), 200
        else:
            logger.warning(
                f"Gagal menghapus membership ID: {id}. Pesan: {result.get('message')}"
            )
            status_code: int = (
                404 if "tidak ditemukan" in result.get("message", "")
                else 400
            )
            return jsonify(result), status_code

    except (RecordNotFoundError, DatabaseException, ServiceLogicError) as e:
        logger.error(f"Error saat {action}: {e}", exc_info=True)
        message = str(e)
        status_code = 500
        if isinstance(e, RecordNotFoundError):
            status_code = 404
        elif "Tidak dapat menghapus" in message:
            status_code = 400
        return jsonify({"success": False, "message": message}), status_code
    
    except Exception as e:
        logger.error(f"Error tak terduga saat {action}: {e}", exc_info=True)
        return (
            jsonify(
                {"success": False, "message": "Kesalahan server tak terduga."}
                ), 500
        )