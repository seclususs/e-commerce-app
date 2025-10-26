from typing import Any, Dict, List, Tuple, Union

from flask import Response, flash, render_template, request

from app.core.db import get_content
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.services.reports.report_service import report_service
from app.utils.export_utils import generate_csv_response
from app.utils.logging_utils import get_logger
from app.utils.route_decorators import admin_required

from . import admin_bp

logger = get_logger(__name__)


@admin_bp.route("/reports")
@admin_required
def admin_reports() -> str:
    start_date: str = request.args.get("start_date")
    end_date: str = request.args.get("end_date")
    logger.debug(
        f"Menghasilkan laporan untuk periode: Awal={start_date}, Akhir={end_date}"
    )

    try:
        sales_summary: Dict[str, Any] = report_service.get_sales_summary(
            start_date, end_date
        )
        product_reports: List[Dict[str, Any]] = (
            report_service.get_product_reports(start_date, end_date)
        )
        customer_reports: List[Dict[str, Any]] = (
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
        logger.info("Semua data laporan berhasil diambil.")
        reports_data: Dict[str, Any] = {
            "sales": sales_summary,
            "products": product_reports,
            "customers": customer_reports,
            "voucher_effectiveness": voucher_effectiveness,
            "cart_analytics": cart_analytics,
            "inventory": inventory_reports,
        }

        return render_template(
            "admin/reports.html", reports=reports_data, content=get_content()
        )
    
    except (DatabaseException, ServiceLogicError) as service_err:
        logger.error(
            f"Kesalahan saat memuat halaman laporan: {service_err}",
            exc_info=True,
        )
        flash("Gagal memuat data laporan.", "danger")
        return render_template(
            "admin/reports.html", reports={}, content=get_content()
        )
    
    except Exception as e:
        logger.error(
            f"Kesalahan tak terduga saat memuat halaman laporan: {e}",
            exc_info=True,
        )
        flash("Gagal memuat data laporan.", "danger")
        return render_template(
            "admin/reports.html", reports={}, content=get_content()
        )


@admin_bp.route("/export/<report_name>")
@admin_required
def export_report(report_name: str) -> Union[Response, Tuple[str, int]]:
    start_date: str = request.args.get("start_date")
    end_date: str = request.args.get("end_date")
    logger.debug(
        f"Mengekspor laporan: {report_name}. Periode: Awal={start_date}, Akhir={end_date}"
    )

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
            logger.info(
                f"Mengekspor laporan penjualan. Ditemukan {len(data)} data."
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
            logger.info(
                f"Mengekspor laporan produk. Ditemukan {len(data)} data."
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
            logger.info(
                f"Mengekspor laporan pelanggan. Ditemukan {len(data)} data."
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
            logger.info(
                f"Mengekspor laporan stok rendah. Ditemukan {len(data)} data."
            )

        elif report_name == "inventory_slow_moving":
            headers = ["Nama Produk", "Stok Saat Ini", "Total Terjual (periode)"]
            data = report_service.get_inventory_slow_moving_for_export(
                start_date, end_date
            )
            logger.info(
                f"Mengekspor laporan produk dengan pergerakan lambat. "
                f"Ditemukan {len(data)} data."
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
            logger.info(
                f"Mengekspor laporan voucher. Ditemukan {len(data)} data."
            )
            
        else:
            logger.warning(
                f"Nama laporan tidak valid diminta untuk diekspor: {report_name}"
            )
            return "Nama laporan tidak valid.", 404

        return generate_csv_response(data, headers, report_name)
    
    except (DatabaseException, ServiceLogicError) as service_err:
        logger.error(
            f"Kesalahan saat mengekspor laporan '{report_name}': {service_err}",
            exc_info=True,
        )
        return "Gagal mengekspor laporan.", 500
    
    except Exception as e:
        logger.error(
            f"Kesalahan tak terduga saat mengekspor laporan '{report_name}': {e}",
            exc_info=True,
        )
        return "Gagal mengekspor laporan.", 500