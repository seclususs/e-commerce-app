import json
from decimal import Decimal
from typing import Any, Dict, Tuple, Union

from flask import Response, flash, jsonify, render_template, request

from app.core.db import get_content
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.services.reports.report_service import report_service
from app.services.utils.scheduler_service import scheduler_service
from app.utils.date_utils import get_date_range
from app.utils.logging_utils import get_logger
from app.utils.route_decorators import admin_required

from . import admin_bp

logger = get_logger(__name__)


def convert_decimals(obj: Any) -> Any:
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj


@admin_bp.route("/dashboard")
@admin_required
def admin_dashboard() -> Union[str, Response, Tuple[Response, int]]:
    period: str = request.args.get("period", "last_7_days")
    custom_start: str = request.args.get("custom_start")
    custom_end: str = request.args.get("custom_end")
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    try:
        start_date_str: str
        end_date_str: str
        start_date_str, end_date_str = get_date_range(
            period, custom_start, custom_end
        )

        if custom_start and custom_end:
            period = "custom"

        stats: Dict[str, Any] = report_service.get_dashboard_stats(
            start_date_str, end_date_str
        )
        stats_converted: Dict[str, Any] = convert_decimals(stats)

        page_title = "Dashboard - Admin"
        header_title = "Dashboard Ringkasan"

        if is_ajax:
            sales_chart_data: Dict[str, Any] = stats_converted[
                "sales_chart_data"
            ]
            top_products_chart: Dict[str, Any] = stats_converted[
                "top_products_chart"
            ]
            low_stock_chart: Dict[str, Any] = stats_converted["low_stock_chart"]
            chart_labels: str = json.dumps(sales_chart_data["labels"])
            chart_data: str = json.dumps(sales_chart_data["data"])
            top_products_chart_labels: str = json.dumps(
                top_products_chart["labels"]
            )
            top_products_chart_data: str = json.dumps(
                top_products_chart["data"]
            )
            low_stock_chart_labels: str = json.dumps(low_stock_chart["labels"])
            low_stock_chart_data: str = json.dumps(low_stock_chart["data"])

            html = render_template(
                "partials/admin/_dashboard.html",
                stats=stats_converted,
                content=get_content(),
                chart_labels=chart_labels,
                chart_data=chart_data,
                top_products_chart_labels=top_products_chart_labels,
                top_products_chart_data=top_products_chart_data,
                low_stock_chart_labels=low_stock_chart_labels,
                low_stock_chart_data=low_stock_chart_data,
                selected_period=period,
                custom_start=custom_start,
                custom_end=custom_end,
            )
            return jsonify(
                {
                    "success": True,
                    "html": html,
                    "page_title": page_title,
                    "header_title": header_title,
                    "stats": stats_converted,
                }
            )

        sales_chart_data: Dict[str, Any] = stats_converted[
            "sales_chart_data"
        ]
        top_products_chart: Dict[str, Any] = stats_converted[
            "top_products_chart"
        ]
        low_stock_chart: Dict[str, Any] = stats_converted["low_stock_chart"]
        chart_labels: str = json.dumps(sales_chart_data["labels"])
        chart_data: str = json.dumps(sales_chart_data["data"])
        top_products_chart_labels: str = json.dumps(
            top_products_chart["labels"]
        )
        top_products_chart_data: str = json.dumps(
            top_products_chart["data"]
        )
        low_stock_chart_labels: str = json.dumps(low_stock_chart["labels"])
        low_stock_chart_data: str = json.dumps(low_stock_chart["data"])

        return render_template(
            "admin/dashboard.html",
            stats=stats_converted,
            content=get_content(),
            chart_labels=chart_labels,
            chart_data=chart_data,
            top_products_chart_labels=top_products_chart_labels,
            top_products_chart_data=top_products_chart_data,
            low_stock_chart_labels=low_stock_chart_labels,
            low_stock_chart_data=low_stock_chart_data,
            selected_period=period,
            custom_start=custom_start,
            custom_end=custom_end,
        )

    except (DatabaseException, ServiceLogicError):
        flash("Gagal memuat data dashboard.", "danger")
        if is_ajax:
            return (
                jsonify(
                    {"success": False, "message": "Gagal memuat data dashboard."}
                ),
                500,
            )
        return render_template(
            "admin/dashboard.html",
            stats={},
            content=get_content(),
            chart_labels="[]",
            chart_data="[]",
            top_products_chart_labels="[]",
            top_products_chart_data="[]",
            low_stock_chart_labels="[]",
            low_stock_chart_data="[]",
        )

    except Exception:
        flash("Gagal memuat data dashboard.", "danger")
        if is_ajax:
            return (
                jsonify(
                    {"success": False, "message": "Kesalahan server internal."}
                ),
                500,
            )
        return render_template(
            "admin/dashboard.html",
            stats={},
            content=get_content(),
            chart_labels="[]",
            chart_data="[]",
            top_products_chart_labels="[]",
            top_products_chart_data="[]",
            low_stock_chart_labels="[]",
            low_stock_chart_data="[]",
        )


@admin_bp.route("/run-scheduler", methods=["POST"])
@admin_required
def run_scheduler() -> Tuple[Response, int]:
    
    try:
        result: Dict[str, Any] = (
            scheduler_service.cancel_expired_pending_orders()
        )
        count: int = result.get("cancelled_count", 0)

        if result.get("success"):
            result["message"] = (
                f"Tugas harian selesai. {count} pesanan "
                f"kedaluwarsa berhasil dibatalkan."
            )
        else:
            result["message"] = result.get(
                "message", "Gagal menjalankan tugas harian."
            )

        return jsonify(result), 200

    except (DatabaseException, ServiceLogicError):
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Gagal menjalankan scheduler "
                    "karena kesalahan layanan.",
                }
            ),
            500,
        )

    except Exception:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Terjadi kesalahan internal "
                    "saat menjalankan scheduler.",
                }
            ),
            500,
        )