from flask import render_template, request
from datetime import datetime, timedelta

from . import admin_bp
from database.db_config import get_db_connection, get_content
from utils.route_decorators import admin_required

def get_date_range(period_str):
    """Mendapatkan rentang tanggal berdasarkan string periode."""
    today = datetime.now()
    if period_str == 'last_30_days':
        start_date = today - timedelta(days=29)
        end_date = today
    elif period_str == 'this_month':
        start_date = today.replace(day=1)
        end_date = today
    else: # Default ke 7 hari terakhir jika tidak ada atau tidak valid
        start_date = today - timedelta(days=6)
        end_date = today
    return start_date.strftime('%Y-%m-%d 00:00:00'), end_date.strftime('%Y-%m-%d 23:59:59')

@admin_bp.route('/dashboard')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    
    # Logika rentang waktu
    period = request.args.get('period', 'last_7_days') # Default 7 hari
    custom_start = request.args.get('custom_start')
    custom_end = request.args.get('custom_end')

    if custom_start and custom_end:
        start_date_str = f"{custom_start} 00:00:00"
        end_date_str = f"{custom_end} 23:59:59"
        period = 'custom'
    else:
        start_date_str, end_date_str = get_date_range(period)

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d %H:%M:%S')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S')

    # Query stats dengan rentang waktu
    total_sales = conn.execute("SELECT SUM(total_amount) FROM orders WHERE status != 'Cancelled' AND order_date BETWEEN ? AND ?", (start_date_str, end_date_str)).fetchone()[0]
    order_count = conn.execute("SELECT COUNT(id) FROM orders WHERE order_date BETWEEN ? AND ?", (start_date_str, end_date_str)).fetchone()[0]
    new_user_count = conn.execute("SELECT COUNT(id) FROM users WHERE created_at BETWEEN ? AND ?", (start_date_str, end_date_str)).fetchone()[0]
    product_count = conn.execute('SELECT COUNT(id) FROM products').fetchone()[0] # Total produk tidak terikat waktu

    # Query kartu baru
    top_products = conn.execute("""
        SELECT p.name, SUM(oi.quantity) as total_sold
        FROM order_items oi JOIN products p ON oi.product_id = p.id JOIN orders o ON oi.order_id = o.id
        WHERE o.status != 'Cancelled' AND o.order_date BETWEEN ? AND ?
        GROUP BY p.id ORDER BY total_sold DESC LIMIT 5
    """, (start_date_str, end_date_str)).fetchall()
    
    low_stock_products = conn.execute("SELECT id, name, stock FROM products WHERE stock > 0 AND stock <= 5 ORDER BY stock ASC LIMIT 5").fetchall()

    # Logika Chart dengan rentang waktu dinamis
    sales_data_raw = conn.execute("""
        SELECT date(order_date) as sale_date, SUM(total_amount) as daily_total
        FROM orders WHERE status != 'Cancelled' AND order_date BETWEEN ? AND ?
        GROUP BY sale_date ORDER BY sale_date ASC
    """, (start_date_str, end_date_str)).fetchall()

    sales_by_date = {row['sale_date']: row['daily_total'] for row in sales_data_raw}
    chart_labels, chart_data = [], []
    delta = end_date.date() - start_date.date()
    for i in range(delta.days + 1):
        current_date = start_date.date() + timedelta(days=i)
        date_str = current_date.strftime('%Y-%m-%d')
        chart_labels.append(current_date.strftime('%d %b'))
        chart_data.append(sales_by_date.get(date_str, 0))

    conn.close()

    stats = {
        'product_count': product_count,
        'order_count': order_count,
        'total_sales': total_sales or 0,
        'new_user_count': new_user_count,
        'top_products': top_products,
        'low_stock_products': low_stock_products
    }
    
    return render_template(
        'admin/dashboard.html', stats=stats, content=get_content(),
        chart_labels=chart_labels, chart_data=chart_data,
        selected_period=period, custom_start=custom_start, custom_end=custom_end
    )
