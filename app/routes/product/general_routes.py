from typing import Any, Dict, List, Optional

import mysql.connector
from flask import Response, redirect, render_template, session, url_for
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursorDict

from app.core.db import get_content, get_db_connection
from app.utils.logging_utils import get_logger
from app.utils.route_decorators import login_required

from . import product_bp

logger = get_logger(__name__)


@product_bp.route("/")
def index() -> str | Response:
    logger.debug("Mengakses rute index '/'.")
    if "user_id" in session:
        logger.info(
            f"Pengguna {session['username']} telah login, "
            "mengarahkan ke halaman produk."
        )
        return redirect(url_for("product.products_page"))

    conn: Optional[MySQLConnection] = None
    cursor: Optional[MySQLCursorDict] = None
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query: str = """
            SELECT p.*, c.name AS category
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            ORDER BY popularity DESC
            LIMIT 4
        """
        cursor.execute(query)
        top_products: List[Dict[str, Any]] = cursor.fetchall()
        logger.info(
            f"Berhasil mengambil {len(top_products)} produk teratas "
            "untuk halaman utama."
        )
        return render_template(
            "public/landing_page.html",
            products=top_products,
            content=get_content(),
            is_homepage=True,
        )

    except mysql.connector.Error as db_err:
        logger.error(
            "Kesalahan database saat mengambil produk teratas "
            f"untuk halaman utama: {db_err}",
            exc_info=True,
        )

    except Exception as e:
        logger.error(
            "Terjadi kesalahan tak terduga saat mengambil produk teratas "
            f"untuk halaman utama: {e}",
            exc_info=True,
        )

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

    return render_template(
        "public/landing_page.html",
        products=[],
        content=get_content(),
        is_homepage=True,
    )


@product_bp.route("/home")
@login_required
def home() -> Response:
    logger.debug(
        "Mengakses '/home', mengarahkan pengguna yang sudah login "
        "ke halaman produk."
    )
    return redirect(url_for("product.products_page"))


@product_bp.route("/about")
def about() -> str:
    logger.debug("Mengakses halaman '/about'.")
    return render_template("public/about.html", content=get_content())