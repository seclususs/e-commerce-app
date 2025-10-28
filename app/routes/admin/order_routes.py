from typing import Any, Dict, List, Tuple, Union

from flask import (
    Response, flash, jsonify, redirect,
    render_template, request, url_for
)

from app.core.db import get_content
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
)
from app.exceptions.service_exceptions import (
    InvalidOperationError, ServiceLogicError
)
from app.services.orders.order_query_service import order_query_service
from app.services.orders.order_update_service import order_update_service
from app.utils.logging_utils import get_logger
from app.utils.route_decorators import admin_required

from . import admin_bp

logger = get_logger(__name__)


@admin_bp.route("/orders")
@admin_required
def admin_orders() -> Union[str, Response, Tuple[Response, int]]:
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    page_title = "Manajemen Pesanan - Admin"
    header_title = "Manajemen Pesanan"

    try:
        status_filter: str = request.args.get("status")
        start_date: str = request.args.get("start_date")
        end_date: str = request.args.get("end_date")
        search_query: str = request.args.get("search")

        orders: List[Dict[str, Any]] = (
            order_query_service.get_filtered_admin_orders(
                status=status_filter,
                start_date=start_date,
                end_date=end_date,
                search=search_query,
            )
        )

        if is_ajax:
            if request.args:
                html: str = render_template(
                    "partials/admin/_order_table_body.html", orders=orders
                )
                return jsonify({"success": True, "html": html})
            else:
                html: str = render_template(
                    "partials/admin/_manage_orders.html",
                    orders=orders,
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

        return render_template(
            "admin/manage_orders.html", orders=orders, content=get_content()
        )

    except (DatabaseException, ServiceLogicError):
        message = "Terjadi kesalahan saat mengambil data pesanan."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        flash(message, "danger")
        return render_template(
            "admin/manage_orders.html", orders=[], content=get_content()
        )
    
    except Exception:
        message = "Terjadi kesalahan saat mengambil data pesanan."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        flash(message, "danger")
        return render_template(
            "admin/manage_orders.html", orders=[], content=get_content()
        )


@admin_bp.route("/order/<int:id>")
@admin_required
def admin_order_detail(id: int) -> Union[str, Response, Tuple[Response, int]]:
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    try:
        order: Dict[str, Any]
        items: List[Dict[str, Any]]
        order, items = order_query_service.get_order_details_for_admin(id)

        page_title = f"Detail Pesanan #{id} - Admin"
        header_title = f"Detail Pesanan #{id}"

        if is_ajax:
            html = render_template(
                "partials/admin/_view_order.html",
                order=order,
                items=items,
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
                "admin/view_order.html",
                order=order,
                items=items,
                content=get_content(),
            )

    except RecordNotFoundError:
        message = "Pesanan tidak ditemukan."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 404
        flash(message, "danger")
        return redirect(url_for("admin.admin_orders"))
    
    except (DatabaseException, ServiceLogicError):
        message = "Terjadi kesalahan saat mengambil detail pesanan."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        flash(message, "danger")
        return redirect(url_for("admin.admin_orders"))
    
    except Exception:
        message = "Terjadi kesalahan saat mengambil detail pesanan."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        flash(message, "danger")
        return redirect(url_for("admin.admin_orders"))


@admin_bp.route("/order/invoice/<int:id>")
@admin_required
def admin_order_invoice(id: int) -> Union[str, Tuple[str, int]]:

    try:
        order: Dict[str, Any]
        items: List[Dict[str, Any]]
        order, items = order_query_service.get_order_details_for_invoice(id)

        return render_template(
            "admin/invoice.html",
            order=order,
            items=items,
            content=get_content(),
        )
    
    except RecordNotFoundError:
        return "Pesanan tidak ditemukan", 404
    
    except (DatabaseException, ServiceLogicError):
        return "Gagal membuat invoice", 500
    
    except Exception:
        return "Gagal membuat invoice", 500


@admin_bp.route("/update_order_status/<int:id>", methods=["POST"])
@admin_required
def update_order_status(id: int) -> Tuple[Response, int]:
    status: str = request.form.get("status")
    tracking_number: str = request.form.get("tracking_number")

    try:
        result: Dict[
            str, Any
        ] = order_update_service.update_order_status_and_tracking(
            id, status, tracking_number
        )

        if result.get("success"):
            if "data" in result and "status_class" in result["data"]:
                result["data"]["status"] = status
                result["data"]["tracking_number"] = tracking_number
                return jsonify(result), 200
            else:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Kesalahan internal: data respons tidak lengkap.",
                        }
                    ),
                    500,
                )
        else:
            status_code: int = 400
            message = result.get("message", "")
            if "tidak ditemukan" in message.lower():
                status_code = 404
            elif "tidak dapat dibatalkan" in message.lower():
                status_code = 400
            return jsonify(result), status_code

    except RecordNotFoundError as rnfe:
        return jsonify({"success": False, "message": str(rnfe)}), 404
    
    except InvalidOperationError as ioe:
        return jsonify({"success": False, "message": str(ioe)}), 400
    
    except (DatabaseException, ServiceLogicError):
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Gagal memperbarui status pesanan karena kesalahan server.",
                }
            ),
            500,
        )
    
    except Exception:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Gagal memperbarui status pesanan karena kesalahan server.",
                }
            ),
            500,
        )