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

    date_filter = " WHERE 1=1 "
    params = []
    if start_date:
        date_filter += " AND o.order_date >= ? "
        params.append(start_date + ' 00:00:00')
    if end_date:
        date_filter += " AND o.order_date <= ? "
        params.append(end_date + ' 23:59:59')
    
    sales_query = f"""SELECT 
                        COALESCE(SUM(o.total_amount), 0) as total_revenue, 
                        COUNT(o.id) as total_orders, 
                        COALESCE(SUM(oi.quantity), 0) as total_items_sold
                     FROM orders o
                     LEFT JOIN order_items oi ON o.id = oi.order_id
                     {date_filter.replace('o.order_date', 'o.order_date')} AND o.status != 'Cancelled'"""
    
    sales_report = conn.execute(sales_query, params).fetchone()

    top_selling_products = conn.execute(f"""
        SELECT p.name, SUM(oi.quantity) as total_sold FROM products p
        JOIN order_items oi ON p.id = oi.product_id
        JOIN orders o ON oi.order_id = o.id
        {date_filter} AND o.status != 'Cancelled'
        GROUP BY p.id ORDER BY total_sold DESC LIMIT 10
    """, params).fetchall()

    most_viewed_products = conn.execute("SELECT name, popularity FROM products ORDER BY popularity DESC LIMIT 10").fetchall()

    top_spenders = conn.execute(f"""
        SELECT u.username, u.email, SUM(o.total_amount) as total_spent FROM users u
        JOIN orders o ON u.id = o.user_id
        {date_filter} AND o.status != 'Cancelled'
        GROUP BY u.id ORDER BY total_spent DESC LIMIT 10
    """, params).fetchall()

    conn.close()

    reports_data = {
        'sales': dict(sales_report),
        'products': {
            'top_selling': top_selling_products,
            'most_viewed': most_viewed_products
        },
        'customers': {
            'top_spenders': top_spenders
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
        # Parameter untuk subquery juga perlu
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