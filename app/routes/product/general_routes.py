from typing import Any, Dict, List, Optional

import mysql.connector
from flask import (
    Response, redirect, render_template, session,
    url_for, request, jsonify, flash
)
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursorDict

from app.core.db import get_content, get_db_connection
from app.utils.logging_utils import get_logger
from app.utils.route_decorators import login_required

from . import product_bp

logger = get_logger(__name__)


@product_bp.route("/")
def index() -> str | Response:
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    logger.debug(f"Mengakses rute index '/' (AJAX: {is_ajax}).")

    if "user_id" in session:
        logger.info(
            f"Pengguna {session['username']} telah login, "
            "mengarahkan ke halaman produk."
        )
        return redirect(url_for("product.products_page"))

    conn: Optional[MySQLConnection] = None
    cursor: Optional[MySQLCursorDict] = None
    page_title = (
        f"{get_content().get('app_name', 'App')} - "
        f"{get_content().get('short_description', 'Tagline')}"
    )

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

        render_args = {
            "products": top_products,
            "content": get_content(),
            "is_homepage": True,
        }

        if is_ajax:
            html = render_template(
                "partials/public/_landing.html", **render_args
            )
            return jsonify(
                {"success": True, "html": html, "page_title": page_title}
            )
        else:
            return render_template(
                "public/landing_page.html", **render_args
            )

    except mysql.connector.Error as db_err:
        logger.error(
            f"Kesalahan database saat mengambil produk teratas: {db_err}",
            exc_info=True,
        )
        message = "Gagal memuat produk teratas."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        
    except Exception as e:
        logger.error(
            f"Terjadi kesalahan tak terduga saat mengambil produk teratas: {e}",
            exc_info=True,
        )
        message = "Gagal memuat produk teratas."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

    render_args_fallback = {
        "products": [],
        "content": get_content(),
        "is_homepage": True,
    }

    if is_ajax:
        html = render_template(
            "partials/public/_landing.html", **render_args_fallback
        )
        return (
            jsonify(
                {
                    "success": False,
                    "html": html,
                    "page_title": page_title,
                    "message": "Gagal memuat konten",
                }
            ),
            500,
        )
    else:
        return render_template(
            "public/landing_page.html", **render_args_fallback
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
def about() -> str | Response:
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    logger.debug(f"Mengakses halaman '/about' (AJAX: {is_ajax}).")
    page_title = f"Tentang Kami - {get_content().get('app_name', 'App')}"

    try:
        if is_ajax:
            html = render_template(
                "partials/public/_about.html", content=get_content()
            )
            return jsonify(
                {"success": True, "html": html, "page_title": page_title}
            )
        else:
            return render_template("public/about.html", content=get_content())
        
    except Exception as e:
        logger.error(
            f"Kesalahan saat me-render halaman tentang (AJAX: {is_ajax}): {e}",
            exc_info=True,
        )
        message = "Gagal memuat halaman Tentang Kami."
        if is_ajax:
            return jsonify({"success": False, "message": message}), 500
        flash(message, "danger")
        return render_template("public/about.html", content=get_content())