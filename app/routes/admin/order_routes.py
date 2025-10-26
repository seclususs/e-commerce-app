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
from app.exceptions.database_exceptions import (
    DatabaseException,
    RecordNotFoundError,
)
from app.exceptions.service_exceptions import (
    InvalidOperationError,
    ServiceLogicError,
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

    try:
        status_filter: str = request.args.get("status")
        start_date: str = request.args.get("start_date")
        end_date: str = request.args.get("end_date")
        search_query: str = request.args.get("search")
        logger.debug(
            f"Mengambil data pesanan dengan filter - "
            f"Status: {status_filter}, Awal: {start_date}, "
            f"Akhir: {end_date}, Pencarian: {search_query}"
        )
        orders: List[Dict[str, Any]] = (
            order_query_service.get_filtered_admin_orders(
                status=status_filter,
                start_date=start_date,
                end_date=end_date,
                search=search_query,
            )
        )
        logger.info(
            f"Berhasil mengambil {len(orders)} data pesanan sesuai filter."
        )

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            logger.debug("Mengembalikan respon JSON untuk permintaan AJAX.")
            html: str = render_template(
                "admin/partials/_order_table_body.html", orders=orders
            )
            return jsonify({"success": True, "html": html})
        
        logger.info("Menampilkan halaman kelola pesanan.")

        return render_template(
            "admin/manage_orders.html", orders=orders, content=get_content()
        )

    except (DatabaseException, ServiceLogicError) as service_err:
        logger.error(
            f"Kesalahan saat mengambil data pesanan: {service_err}",
            exc_info=True,
        )
        flash("Terjadi kesalahan saat mengambil data pesanan.", "danger")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return (
                jsonify(
                    {"success": False, "message": "Gagal mengambil data pesanan."}
                ),
                500,
            )
        return render_template(
            "admin/manage_orders.html", orders=[], content=get_content()
        )

    except Exception as e:
        logger.error(
            f"Kesalahan tak terduga saat mengambil data pesanan: {e}",
            exc_info=True,
        )
        flash("Terjadi kesalahan saat mengambil data pesanan.", "danger")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return (
                jsonify(
                    {"success": False, "message": "Gagal mengambil data pesanan."}
                ),
                500,
            )
        return render_template(
            "admin/manage_orders.html", orders=[], content=get_content()
        )


@admin_bp.route("/order/<int:id>")
@admin_required
def admin_order_detail(id: int) -> Union[str, Response]:
    logger.debug(f"Mengambil detail pesanan dengan ID: {id}")
    try:
        order: Dict[str, Any]
        items: List[Dict[str, Any]]
        order, items = order_query_service.get_order_details_for_admin(id)
        logger.info(
            f"Detail pesanan berhasil diambil untuk ID {id}. "
            f"Jumlah item: {len(items)}"
        )
        return render_template(
            "admin/view_order.html",
            order=order,
            items=items,
            content=get_content(),
        )

    except RecordNotFoundError:
        logger.warning(f"Pesanan dengan ID {id} tidak ditemukan.")
        flash("Pesanan tidak ditemukan.", "danger")
        return redirect(url_for("admin.admin_orders"))

    except (DatabaseException, ServiceLogicError) as service_err:
        logger.error(
            f"Kesalahan saat mengambil detail pesanan untuk ID {id}: "
            f"{service_err}",
            exc_info=True,
        )
        flash("Terjadi kesalahan saat mengambil detail pesanan.", "danger")
        return redirect(url_for("admin.admin_orders"))

    except Exception as e:
        logger.error(
            f"Kesalahan tak terduga saat mengambil detail pesanan ID {id}: {e}",
            exc_info=True,
        )
        flash("Terjadi kesalahan saat mengambil detail pesanan.", "danger")
        return redirect(url_for("admin.admin_orders"))


@admin_bp.route("/order/invoice/<int:id>")
@admin_required
def admin_order_invoice(id: int) -> Union[str, Tuple[str, int]]:
    logger.debug(f"Menghasilkan invoice untuk pesanan ID: {id}")

    try:
        order: Dict[str, Any]
        items: List[Dict[str, Any]]
        order, items = order_query_service.get_order_details_for_invoice(id)
        logger.info(f"Data invoice berhasil diambil untuk pesanan ID: {id}")
        return render_template(
            "admin/invoice.html",
            order=order,
            items=items,
            content=get_content(),
        )

    except RecordNotFoundError:
        logger.warning(
            f"Pesanan dengan ID {id} tidak ditemukan saat membuat invoice."
        )
        return "Pesanan tidak ditemukan", 404

    except (DatabaseException, ServiceLogicError) as service_err:
        logger.error(
            f"Kesalahan saat membuat invoice untuk pesanan ID {id}: "
            f"{service_err}",
            exc_info=True,
        )
        return "Gagal membuat invoice", 500

    except Exception as e:
        logger.error(
            f"Kesalahan tak terduga saat membuat invoice untuk pesanan ID {id}: {e}",
            exc_info=True,
        )
        return "Gagal membuat invoice", 500


@admin_bp.route("/update_order_status/<int:id>", methods=["POST"])
@admin_required
def update_order_status(id: int) -> Tuple[Response, int]:
    status: str = request.form.get("status")
    tracking_number: str = request.form.get("tracking_number")
    logger.debug(
        f"Memperbarui pesanan ID: {id}. "
        f"Status baru: {status}, Nomor resi: {tracking_number}"
    )

    try:
        result: Dict[str, Any] = (
            order_update_service.update_order_status_and_tracking(
                id, status, tracking_number
            )
        )

        if result.get("success"):
            logger.info(
                f"Pesanan ID {id} berhasil diperbarui. "
                f"Status: {status}, Resi: {tracking_number}. "
                f"Pesan: {result.get('message')}"
            )
            return jsonify(result), 200
        
        else:
            logger.warning(
                f"Gagal memperbarui pesanan ID {id}. "
                f"Alasan: {result.get('message')}"
            )
            status_code: int = 500
            if isinstance(result.get("exception"), RecordNotFoundError):
                status_code = 404
            elif isinstance(result.get("exception"), InvalidOperationError):
                status_code = 400
            return jsonify(result), status_code

    except RecordNotFoundError as rnfe:
        logger.warning(f"Pembaruan gagal: Pesanan ID {id} tidak ditemukan: {rnfe}")
        return jsonify({"success": False, "message": str(rnfe)}), 404

    except InvalidOperationError as ioe:
        logger.warning(
            f"Pembaruan gagal: Operasi tidak valid untuk pesanan ID {id}: {ioe}"
        )
        return jsonify({"success": False, "message": str(ioe)}), 400

    except (DatabaseException, ServiceLogicError) as service_err:
        logger.error(
            f"Kesalahan saat memperbarui status pesanan untuk ID {id}: "
            f"{service_err}",
            exc_info=True,
        )
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Gagal memperbarui status pesanan "
                    "karena kesalahan server.",
                }
            ),
            500,
        )

    except Exception as e:
        logger.error(
            f"Kesalahan tak terduga saat memperbarui status pesanan ID {id}: {e}",
            exc_info=True,
        )
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Gagal memperbarui status pesanan "
                    "karena kesalahan server.",
                }
            ),
            500,
        )