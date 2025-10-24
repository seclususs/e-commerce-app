from flask import render_template, request, jsonify, flash
from datetime import datetime, timedelta
import json
from decimal import Decimal
from app.core.db import get_content
from app.utils.route_decorators import admin_required
from app.services.utils.scheduler_service import scheduler_service
from app.services.reports.report_service import report_service
from app.utils.date_utils import get_date_range
from app.utils.logging_utils import get_logger
from . import admin_bp

logger = get_logger(__name__)


def convert_decimals(obj):
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj


@admin_bp.route('/dashboard')
@admin_required
def admin_dashboard():
    period = request.args.get('period', 'last_7_days')
    custom_start = request.args.get('custom_start')
    custom_end = request.args.get('custom_end')

    logger.debug(
        f"Mengakses halaman dashboard dengan periode: {period}, "
        f"tanggal awal: {custom_start}, tanggal akhir: {custom_end}"
    )

    try:
        start_date_str, end_date_str = get_date_range(
            period, custom_start, custom_end
        )
        logger.info(
            f"Rentang tanggal yang dihitung: {start_date_str} hingga {end_date_str}"
        )

        if custom_start and custom_end:
            period = 'custom'

        stats = report_service.get_dashboard_stats(
            start_date_str, end_date_str
        )
        stats_converted = convert_decimals(stats)
        logger.info("Statistik dashboard berhasil diambil dan dikonversi.")

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            logger.debug("Menanggapi permintaan AJAX dengan JSON.")
            return jsonify({
                'success': True,
                'data': {
                    'stats': stats_converted,
                    'selected_period': period,
                    'custom_start': custom_start,
                    'custom_end': custom_end
                }
            })

        sales_chart_data = stats_converted['sales_chart_data']
        top_products_chart = stats_converted['top_products_chart']
        low_stock_chart = stats_converted['low_stock_chart']

        chart_labels = json.dumps(sales_chart_data['labels'])
        chart_data = json.dumps(sales_chart_data['data'])
        top_products_chart_labels = json.dumps(top_products_chart['labels'])
        top_products_chart_data = json.dumps(top_products_chart['data'])
        low_stock_chart_labels = json.dumps(low_stock_chart['labels'])
        low_stock_chart_data = json.dumps(low_stock_chart['data'])

        logger.info("Menampilkan template dashboard.")
        return render_template(
            'admin/dashboard.html',
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
            custom_end=custom_end
        )

    except Exception as e:
        logger.error(
            f"Terjadi kesalahan saat memuat dashboard: {e}", 
            exc_info=True
        )
        flash("Gagal memuat data dashboard.", "danger")
        return render_template(
            'admin/dashboard.html',
            stats={},
            content=get_content(),
            chart_labels='[]',
            chart_data='[]',
            top_products_chart_labels='[]',
            top_products_chart_data='[]',
            low_stock_chart_labels='[]',
            low_stock_chart_data='[]'
        )


@admin_bp.route('/run-scheduler', methods=['POST'])
@admin_required
def run_scheduler():
    logger.info("Menjalankan scheduler secara manual oleh admin.")

    try:
        result = scheduler_service.cancel_expired_pending_orders()
        count = result.get('cancelled_count', 0)

        if result.get('success'):
            result['message'] = (
                f"Tugas harian selesai. {count} pesanan kedaluwarsa berhasil dibatalkan."
            )
            logger.info(
                f"Scheduler manual berhasil dijalankan. {count} pesanan dibatalkan."
            )
        else:
            result['message'] = result.get(
                'message', 'Gagal menjalankan tugas harian.'
            )
            logger.warning(
                f"Scheduler manual gagal dijalankan. Alasan: {result.get('message')}"
            )

        return jsonify(result)

    except Exception as e:
        logger.error(
            f"Terjadi kesalahan saat menjalankan scheduler manual: {e}",
            exc_info=True
        )
        return jsonify({
            'success': False,
            'message': 'Terjadi kesalahan internal saat menjalankan scheduler.'
        }), 500