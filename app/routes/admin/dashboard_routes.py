from flask import render_template, request, jsonify
from datetime import datetime, timedelta
import json

from . import admin_bp
from db.db_config import get_content
from utils.route_decorators import admin_required
from services.utils.scheduler_service import scheduler_service
from services.reports.report_service import report_service
from utils.date_utils import get_date_range


@admin_bp.route('/dashboard')
@admin_required
def admin_dashboard():
    period = request.args.get('period', 'last_7_days')
    custom_start = request.args.get('custom_start')
    custom_end = request.args.get('custom_end')

    start_date_str, end_date_str = get_date_range(period, custom_start, custom_end)

    if custom_start and custom_end:
        period = 'custom'

    stats = report_service.get_dashboard_stats(start_date_str, end_date_str)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'data': {
                'stats': stats,
                'selected_period': period,
                'custom_start': custom_start,
                'custom_end': custom_end
            }
        })

    sales_chart_data = stats['sales_chart_data']
    top_products_chart = stats['top_products_chart']
    low_stock_chart = stats['low_stock_chart']

    chart_labels = json.dumps(sales_chart_data['labels'])
    chart_data = json.dumps(sales_chart_data['data'])
    top_products_chart_labels = json.dumps(top_products_chart['labels'])
    top_products_chart_data = json.dumps(top_products_chart['data'])
    low_stock_chart_labels = json.dumps(low_stock_chart['labels'])
    low_stock_chart_data = json.dumps(low_stock_chart['data'])

    return render_template(
        'admin/dashboard.html',
        stats=stats,
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


@admin_bp.route('/run-scheduler', methods=['POST'])
@admin_required
def run_scheduler():
    result = scheduler_service.cancel_expired_pending_orders()
    count = result.get('cancelled_count', 0)
    if result.get('success'):
        result['message'] = f"Tugas harian selesai. {count} pesanan kedaluwarsa berhasil dibatalkan."
    else:
        result['message'] = result.get('message', 'Gagal menjalankan tugas harian.')

    return jsonify(result)