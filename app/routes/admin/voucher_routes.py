from typing import Any, Dict, List, Tuple, Union

from flask import Response, flash, jsonify, render_template, request

from app.core.db import get_content
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
)
from app.exceptions.service_exceptions import ServiceLogicError
from app.services.orders.voucher_service import voucher_service
from app.utils.logging_utils import get_logger
from app.utils.route_decorators import admin_required

from . import admin_bp

logger = get_logger(__name__)


@admin_bp.route("/vouchers", methods=["GET", "POST"])
@admin_required
def admin_vouchers() -> Union[str, Response, Tuple[Response, int]]:
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method == "POST":
        code: str = (request.form.get("code") or "").upper().strip()
        voucher_type: str = request.form.get("type")
        value: str = request.form.get("value")
        min_purchase: str = request.form.get("min_purchase_amount")
        max_uses: str = request.form.get("max_uses")

        try:
            result: Dict[str, Any] = voucher_service.add_voucher(
                code, voucher_type, value, min_purchase, max_uses
            )

            if result.get("success"):
                html: str = render_template(
                    "partials/admin/_voucher_row.html",
                    voucher=result["data"],
                )
                result["html"] = html
                return jsonify(result), 200
            else:
                status_code: int = (
                    409
                    if "sudah terdaftar" in result.get("message", "").lower()
                    else 400
                )
                return jsonify(result), status_code

        except ValidationError as ve:
            return jsonify({"success": False, "message": str(ve)}), 400
        
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
                        "message": "Gagal menambahkan voucher karena kesalahan server.",
                    }
                ),
                500,
            )

    page_title = "Manajemen Voucher - Admin"
    header_title = "Manajemen Voucher Diskon"

    try:
        vouchers: List[Dict[str, Any]] = voucher_service.get_all_vouchers()

        if is_ajax:
            html = render_template(
                "partials/admin/_manage_vouchers.html",
                vouchers=vouchers,
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
            return render_template(
                "admin/manage_vouchers.html",
                vouchers=vouchers,
                content=get_content(),
            )

    except (DatabaseException, ServiceLogicError):
        message = "Gagal memuat halaman voucher."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        flash(message, "danger")
        return render_template(
            "admin/manage_vouchers.html", vouchers=[], content=get_content()
        )
    
    except Exception:
        message = "Gagal memuat halaman voucher."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        flash(message, "danger")
        return render_template(
            "admin/manage_vouchers.html", vouchers=[], content=get_content()
        )


@admin_bp.route("/vouchers/delete/<int:id>", methods=["POST"])
@admin_required
def delete_voucher(id: int) -> Tuple[Response, int]:

    try:
        result: Dict[str, Any] = voucher_service.delete_voucher_by_id(id)

        if result.get("success"):
            return jsonify(result), 200
        else:
            status_code: int = (
                404
                if "tidak ditemukan" in result.get("message", "").lower()
                else 500
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
                    "message": "Gagal menghapus voucher karena kesalahan server.",
                }
            ),
            500,
        )


@admin_bp.route("/vouchers/toggle/<int:id>", methods=["POST"])
@admin_required
def toggle_voucher(id: int) -> Tuple[Response, int]:

    try:
        result: Dict[str, Any] = voucher_service.toggle_voucher_status(id)

        if result.get("success"):
            result["data"] = {"is_active": result.get("is_active")}
            return jsonify(result), 200
        else:
            status_code: int = (
                404
                if "tidak ditemukan" in result.get("message", "").lower()
                else 500
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
                    "message": "Gagal mengubah status voucher karena kesalahan server.",
                }
            ),
            500,
        )