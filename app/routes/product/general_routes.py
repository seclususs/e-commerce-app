from flask import render_template, session, redirect, url_for
from db.db_config import get_db_connection, get_content
from utils.route_decorators import login_required
from . import product_bp


@product_bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('product.products_page'))
    conn = get_db_connection()
    top_products = conn.execute('SELECT p.*, c.name as category FROM products p LEFT JOIN categories c ON p.category_id = c.id ORDER BY popularity DESC LIMIT 4').fetchall()
    conn.close()
    return render_template('public/landing_page.html', products=top_products, content=get_content(), is_homepage=True)


@product_bp.route('/home')
@login_required
def home():
    return redirect(url_for('product.products_page'))


@product_bp.route('/about')
def about():
    return render_template('public/about.html', content=get_content())