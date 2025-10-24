from flask import render_template, session, redirect, url_for
from app.core.db import get_db_connection, get_content
from app.utils.route_decorators import login_required
from app.utils.logging_utils import get_logger
from . import product_bp

logger = get_logger(__name__)


@product_bp.route('/')
def index():
    logger.debug("Mengakses rute index '/'.")

    if 'user_id' in session:
        logger.info(
            f"Pengguna {session['username']} telah login, mengarahkan ke halaman produk."
        )
        return redirect(url_for('product.products_page'))

    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            '''
            SELECT p.*, c.name AS category
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            ORDER BY popularity DESC
            LIMIT 4
            '''
        )
        top_products = cursor.fetchall()
        logger.info(f"Berhasil mengambil {len(top_products)} produk teratas untuk halaman utama.")

        return render_template(
            'public/landing_page.html',
            products=top_products,
            content=get_content(),
            is_homepage=True
        )

    except Exception as e:
        logger.error(
            f"Terjadi kesalahan saat mengambil produk teratas untuk halaman utama: {e}",
            exc_info=True
        )
        return render_template(
            'public/landing_page.html',
            products=[],
            content=get_content(),
            is_homepage=True
        )

    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


@product_bp.route('/home')
@login_required
def home():
    logger.debug(
        "Mengakses '/home', mengarahkan pengguna yang sudah login ke halaman produk."
    )
    return redirect(url_for('product.products_page'))


@product_bp.route('/about')
def about():
    logger.debug("Mengakses halaman '/about'.")
    return render_template(
        'public/about.html',
        content=get_content()
    )