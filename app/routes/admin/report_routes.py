from typing import Any, Dict, List, Tuple, Union

from flask import Response, flash, jsonify, render_template, request

from app.core.db import get_content
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.services.reports.report_service import report_service
from app.utils.export_utils import generate_csv_response
from app.utils.logging_utils import get_logger
from app.utils.route_decorators import admin_required

from . import admin_bp

logger = get_logger(__name__)


def get_default_reports_data() -> Dict[str, Any]:
    return {
        "sales": {
            "total_revenue": 0,
            "total_orders": 0,
            "total_items_sold": 0
        },
        "products": {
            "top_selling": [],
            "most_viewed": []
        },
        "customers": {
            "top_spenders": []
        },
        "voucher_effectiveness": [],
        "cart_analytics": {
            "abandonment_rate": 0,
            "carts_created": 0,
            "orders_completed": 0
        },
        "inventory": {
            "total_value": 0,
            "low_stock": [],
            "slow_moving": []
        },
    }

@admin_bp.route("/reports")
@admin_required
def admin_reports() -> Union[str, Response, Tuple[Response, int]]:
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    start_date: str = request.args.get("start_date")
    end_date: str = request.args.get("end_date")
    page_title = "Laporan & Analitik - Admin"
    header_title = "Laporan & Analitik"

    try:
        sales_summary: Dict[str, Any] = report_service.get_sales_summary(
            start_date, end_date
        )
        product_reports: Dict[str, Any] = (
            report_service.get_product_reports(start_date, end_date)
        )
        customer_reports: Dict[str, Any] = (
            report_service.get_customer_reports(start_date, end_date)
        )
        voucher_effectiveness: List[Dict[str, Any]] = (
            report_service.get_voucher_effectiveness(start_date, end_date)
        )
        cart_analytics: Dict[str, Any] = report_service.get_cart_analytics(
            start_date, end_date
        )
        inventory_reports: Dict[str, Any] = (
            report_service.get_inventory_reports(start_date, end_date)
        )

        reports_data: Dict[str, Any] = {
            "sales": sales_summary,
            "products": product_reports,
            "customers": customer_reports,
            "voucher_effectiveness": voucher_effectiveness,
            "cart_analytics": cart_analytics,
            "inventory": inventory_reports,
        }

        if is_ajax:
            html = render_template(
                "partials/admin/_reports.html",
                reports=reports_data,
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
                "admin/reports.html",
                reports=reports_data,
                content=get_content(),
            )

    except (DatabaseException, ServiceLogicError) as e:
        logger.error(f"Gagal memuat laporan: {e}", exc_info=True)
        message = "Gagal memuat data laporan."
        reports_data = get_default_reports_data() # PERBAIKAN
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        flash(message, "danger")
        return render_template(
            "admin/reports.html", reports=reports_data, content=get_content()
        )
    
    except Exception as e:
        logger.error(f"Error tidak terduga saat memuat laporan: {e}", exc_info=True)
        message = "Gagal memuat data laporan."
        reports_data = get_default_reports_data()
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        flash(message, "danger")
        return render_template(
            "admin/reports.html", reports=reports_data, content=get_content()
        )


@admin_bp.route("/export/<report_name>")
@admin_required
def export_report(report_name: str) -> Union[Response, Tuple[str, int]]:
    start_date: str = request.args.get("start_date")
    end_date: str = request.args.get("end_date")
    data: List[Dict[str, Any]] = []
    headers: List[str] = []

    try:
        if report_name == "sales":
            headers = [
                "ID Pesanan",
                "Tanggal",
                "Nama Pelanggan",
                "Email Pelanggan",
                "Subtotal",
                "Diskon",
                "Ongkir",
                "Total",
                "Status",
                "Metode Pembayaran",
                "Voucher",
            ]
            data = report_service.get_full_sales_data_for_export(
                start_date, end_date
            )

        elif report_name == "products":
            headers = [
                "ID Produk",
                "Nama Produk",
                "Kategori",
                "SKU",
                "Harga Asli",
                "Harga Diskon",
                "Stok",
                "Terjual (periode)",
                "Dilihat (total)",
            ]
            data = report_service.get_full_products_data_for_export(
                start_date, end_date
            )

        elif report_name == "customers":
            headers = [
                "ID Pelanggan",
                "Username",
                "Email",
                "Total Belanja (periode)",
                "Jumlah Pesanan (periode)",
            ]
            data = report_service.get_full_customers_data_for_export(
                start_date, end_date
            )

        elif report_name == "inventory_low_stock":
            headers = [
                "Nama Produk/Varian",
                "Sisa Stok",
                "Tipe",
                "ID Produk",
                "ID Varian",
                "SKU",
            ]
            data = report_service.get_inventory_low_stock_for_export()

        elif report_name == "inventory_slow_moving":
            headers = ["Nama Produk", "Stok Saat Ini", "Total Terjual (periode)"]
            data = report_service.get_inventory_slow_moving_for_export(
                start_date, end_date
            )

        elif report_name == "vouchers":
            headers = [
                "Kode Voucher",
                "Tipe",
                "Nilai",
                "Jumlah Penggunaan (periode)",
                "Total Diskon (periode)",
            ]
            data = report_service.get_full_vouchers_data_for_export(
                start_date, end_date
            )

        else:
            return "Nama laporan tidak valid.", 404

        return generate_csv_response(data, headers, report_name)
    
    except (DatabaseException, ServiceLogicError):
        return "Gagal mengekspor laporan.", 500
    
    except Exception:
        return "Gagal mengekspor laporan.", 500