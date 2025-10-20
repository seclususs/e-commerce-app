import csv
from io import StringIO
from datetime import datetime
from flask import render_template, request, Response

from . import admin_bp
from database.db_config import get_db_connection, get_content
from utils.route_decorators import admin_required

@admin_bp.route('/reports')
@admin_required
def admin_reports():
    conn = get_db_connection()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Base date filter clause
    date_filter = " WHERE o.status != 'Cancelled' "
    params = []
    if start_date:
        date_filter += " AND o.order_date >= ? "
        params.append(start_date + ' 00:00:00')
    if end_date:
        date_filter += " AND o.order_date <= ? "
        params.append(end_date + ' 23:59:59')

    # Sales Report
    sales_query = f"""SELECT 
                        COALESCE(SUM(o.total_amount), 0) as total_revenue, 
                        COUNT(o.id) as total_orders, 
                        COALESCE(SUM(oi.quantity), 0) as total_items_sold
                     FROM orders o
                     LEFT JOIN order_items oi ON o.id = oi.order_id
                     {date_filter.replace('o.order_date', 'o.order_date')}"""
    sales_report = conn.execute(sales_query, params).fetchone()

    # Product Reports
    top_selling_products = conn.execute(f"""
        SELECT p.name, SUM(oi.quantity) as total_sold FROM products p
        JOIN order_items oi ON p.id = oi.product_id
        JOIN orders o ON oi.order_id = o.id
        {date_filter}
        GROUP BY p.id ORDER BY total_sold DESC LIMIT 10
    """, params).fetchall()
    most_viewed_products = conn.execute("SELECT name, popularity FROM products ORDER BY popularity DESC LIMIT 10").fetchall()

    # Customer Reports
    top_spenders = conn.execute(f"""
        SELECT u.username, u.email, SUM(o.total_amount) as total_spent FROM users u
        JOIN orders o ON u.id = o.user_id
        {date_filter}
        GROUP BY u.id ORDER BY total_spent DESC LIMIT 10
    """, params).fetchall()
    
    # Voucher Effectiveness Report
    voucher_effectiveness = conn.execute(f"""
        SELECT 
            voucher_code, 
            COUNT(o.id) AS usage_count, 
            SUM(o.discount_amount) AS total_discount
        FROM orders o
        {date_filter.replace('o.order_date', 'o.order_date')} AND o.voucher_code IS NOT NULL
        GROUP BY o.voucher_code 
        ORDER BY usage_count DESC;
    """, params).fetchall()

    total_carts_created_row = conn.execute("SELECT COUNT(DISTINCT user_id) FROM user_carts").fetchone()
    total_carts_created = total_carts_created_row[0] if total_carts_created_row else 0
    
    total_orders_completed_row = conn.execute(f"SELECT COUNT(DISTINCT user_id) FROM orders o {date_filter}", params).fetchone()
    total_orders_completed = total_orders_completed_row[0] if total_orders_completed_row else 0
    
    abandonment_rate = (1 - (total_orders_completed / total_carts_created)) * 100 if total_carts_created > 0 else 0

    inventory_value_row = conn.execute("""
        SELECT SUM(total_value) 
        FROM (
            SELECT p.price * p.stock as total_value FROM products p WHERE p.has_variants = 0
            UNION ALL 
            SELECT p.price * pv.stock as total_value FROM product_variants pv JOIN products p ON pv.product_id = p.id
        )
    """).fetchone()
    total_inventory_value = inventory_value_row[0] if inventory_value_row else 0

    slow_moving_products = conn.execute(f"""
        SELECT p.name, p.stock, COALESCE(SUM(oi.quantity), 0) AS total_sold
        FROM products p
        LEFT JOIN order_items oi ON p.id = oi.product_id
        LEFT JOIN orders o ON oi.order_id = o.id AND o.status != 'Cancelled'
        GROUP BY p.id ORDER BY total_sold ASC, p.stock DESC LIMIT 10
    """).fetchall()

    low_stock_products = conn.execute("""
        SELECT name, stock, 'Produk Utama' as type, id as product_id, null as variant_id 
        FROM products 
        WHERE has_variants = 0 AND stock <= 5 AND stock > 0 
        UNION ALL 
        SELECT p.name || ' (' || pv.size || ')' as name, pv.stock, 'Varian' as type, p.id as product_id, pv.id as variant_id 
        FROM product_variants pv 
        JOIN products p ON pv.product_id = p.id 
        WHERE pv.stock <= 5 AND pv.stock > 0 
        ORDER BY stock ASC
    """).fetchall()

    conn.close()

    reports_data = {
        'sales': dict(sales_report),
        'products': {
            'top_selling': top_selling_products,
            'most_viewed': most_viewed_products
        },
        'customers': {
            'top_spenders': top_spenders
        },
        'voucher_effectiveness': voucher_effectiveness,
        'cart_analytics': {
            'abandonment_rate': round(abandonment_rate, 2),
            'carts_created': total_carts_created,
            'orders_completed': total_orders_completed
        },
        'inventory': {
            'total_value': total_inventory_value,
            'slow_moving': slow_moving_products,
            'low_stock': low_stock_products
        }
    }
    return render_template('admin/reports.html', reports=reports_data, content=get_content())

@admin_bp.route('/export/<report_name>')
@admin_required
def export_report(report_name):
    conn = get_db_connection()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    si = StringIO()
    cw = csv.writer(si)

    date_filter = " WHERE 1=1 "
    params = []
    if start_date:
        date_filter += " AND o.order_date >= ? "
        params.append(start_date)
    if end_date:
        date_filter += " AND o.order_date <= ? "
        params.append(end_date)

    if report_name == 'sales':
        headers = ['ID Pesanan', 'Tanggal', 'Nama Pelanggan', 'Total', 'Status']
        query = f"SELECT o.id, o.order_date, o.shipping_name, o.total_amount, o.status FROM orders o {date_filter} AND o.status != 'Cancelled' ORDER BY o.order_date DESC"
        data = conn.execute(query, params).fetchall()
    elif report_name == 'products':
        headers = ['ID Produk', 'Nama Produk', 'Terjual', 'Dilihat']
        query = f"""
            SELECT p.id, p.name, COALESCE(SUM(oi.quantity), 0) as total_sold, p.popularity
            FROM products p
            LEFT JOIN order_items oi ON p.id = oi.product_id
            LEFT JOIN orders o ON oi.order_id = o.id AND (o.status != 'Cancelled' {date_filter.replace('WHERE 1=1', '')})
            GROUP BY p.id ORDER BY total_sold DESC
        """
        sub_params = [p for p in params]
        data = conn.execute(query, sub_params).fetchall()
    elif report_name == 'customers':
        headers = ['ID Pelanggan', 'Username', 'Email', 'Total Belanja']
        query = f"""
            SELECT u.id, u.username, u.email, SUM(o.total_amount) as total_spent FROM users u
            JOIN orders o ON u.id = o.user_id
            {date_filter} AND o.status != 'Cancelled'
            GROUP BY u.id ORDER BY total_spent DESC
        """
        data = conn.execute(query, params).fetchall()
    else:
        conn.close()
        return "Laporan tidak valid", 404

    cw.writerow(headers)
    for row in data:
        cw.writerow(row)
    
    conn.close()
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={report_name}_report_{datetime.now().strftime('%Y%m%d')}.csv"}
    )