from typing import Any, Dict, List, Optional, Tuple

from flask import (
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.core.db import get_content
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import (
    DatabaseException,
    RecordNotFoundError,
)
from app.exceptions.service_exceptions import (
    InvalidOperationError,
    ServiceLogicError,
)
from app.services.products.product_query_service import product_query_service
from app.services.products.review_service import review_service
from app.utils.logging_utils import get_logger
from app.utils.route_decorators import login_required

from . import product_bp

logger = get_logger(__name__)


@product_bp.route("/product/<int:id>")
def product_detail(id: int) -> str | Response:
    logger.debug(f"Mengambil halaman detail produk untuk ID: {id}")

    try:
        product: Optional[Dict[str, Any]] = (
            product_query_service.get_product_by_id(id)
        )

        if product is None:
            logger.warning(f"Produk dengan ID {id} tidak ditemukan.")
            raise RecordNotFoundError("Produk tidak ditemukan.")

        reviews: List[Dict[str, Any]] = (
            review_service.get_reviews_for_product(id)
        )
        logger.info(
            f"Berhasil mengambil {len(reviews)} ulasan untuk produk ID {id}."
        )
        related_products: List[Dict[str, Any]] = []
        category_id: Optional[Any] = product.get("category_id")

        if category_id:
            related_products = product_query_service.get_related_products(
                id, category_id
            )
            logger.info(
                f"Berhasil mengambil {len(related_products)} produk terkait."
            )

        user_id: Optional[Any] = session.get("user_id")
        can_review: bool = False

        if user_id:
            can_review = review_service.check_user_can_review(user_id, id)
            logger.debug(
                f"Pengguna {user_id} dapat memberi ulasan untuk produk {id}: "
                f"{can_review}"
            )

        return render_template(
            "public/product_detail.html",
            product=product,
            reviews=reviews,
            related_products=related_products,
            content=get_content(),
            can_review=can_review,
        )

    except RecordNotFoundError as rnfe:
        logger.warning(
            f"Produk atau data terkait tidak ditemukan untuk ID {id}: {rnfe}"
        )
        flash(str(rnfe), "danger")
        return redirect(url_for("product.products_page"))
    
    except (DatabaseException, ServiceLogicError) as service_err:
        logger.error(
            "Kesalahan service/DB saat memuat halaman detail produk "
            f"untuk ID {id}: {service_err}",
            exc_info=True,
        )
        flash("Gagal memuat detail produk.", "danger")
        return redirect(url_for("product.products_page"))
    
    except Exception as e:
        logger.error(
            "Kesalahan tak terduga saat memuat halaman detail produk "
            f"untuk ID {id}: {e}",
            exc_info=True,
        )
        flash(
            "Gagal memuat detail produk karena kesalahan tak terduga.",
            "danger",
        )
        return redirect(url_for("product.products_page"))


@product_bp.route("/product/<int:id>/add_review", methods=["POST"])
@login_required
def add_review(id: int) -> Response | Tuple[Response, int]:
    rating: Optional[str] = request.form.get("rating")
    comment: Optional[str] = request.form.get("comment")
    user_id: Any = session["user_id"]

    logger.debug(
        f"Pengguna {user_id} mencoba menambahkan ulasan untuk produk {id}. "
        f"Rating: {rating}"
    )
    is_ajax: bool = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    try:
        if not rating or not comment or not comment.strip():
            raise ValidationError("Rating dan komentar tidak boleh kosong.")

        result: Dict[str, Any] = review_service.add_review(
            user_id, id, rating, comment
        )

        if is_ajax:
            if result.get("success"):
                logger.info(
                    f"Ulasan berhasil ditambahkan melalui AJAX untuk produk {id} "
                    f"oleh pengguna {user_id}."
                )
                new_review: Optional[Dict[str, Any]] = (
                    review_service.get_review_by_id(result["review_id"])
                )
                review_html: str = (
                    render_template(
                        "partials/_review.html", review=new_review
                    )
                    if new_review
                    else ""
                )
                return jsonify(
                    {
                        "success": True,
                        "message": result["message"],
                        "review_html": review_html,
                    }
                )
            
            else:
                logger.warning(
                    "Gagal menambahkan ulasan melalui AJAX untuk produk "
                    f"{id} oleh pengguna {user_id}. Alasan: {result['message']}"
                )
                raise InvalidOperationError(result["message"])

        flash(result["message"], "success" if result["success"] else "danger")

        if result["success"]:
            logger.info(
                "Ulasan berhasil ditambahkan untuk produk {id} oleh "
                f"pengguna {user_id}."
            )

        else:
            logger.warning(
                f"Gagal menambahkan ulasan untuk produk {id} oleh pengguna "
                f"{user_id}. Alasan: {result['message']}"
            )
            
        return redirect(url_for("product.product_detail", id=id))

    except ValidationError as ve:
        logger.warning(
            f"Gagal menambahkan ulasan untuk produk {id} oleh pengguna "
            f"{user_id}: Validasi gagal: {ve}"
        )
        if is_ajax:
            return jsonify({"success": False, "message": str(ve)}), 400
        flash(str(ve), "danger")
        return redirect(url_for("product.product_detail", id=id))

    except InvalidOperationError as ioe:
        logger.warning(
            "Operasi tidak valid saat menambahkan ulasan produk {id} "
            f"oleh user {user_id}: {ioe}"
        )
        if is_ajax:
            return jsonify({"success": False, "message": str(ioe)}), 400
        flash(str(ioe), "warning")
        return redirect(url_for("product.product_detail", id=id))

    except (DatabaseException, ServiceLogicError) as service_err:
        logger.error(
            "Kesalahan service/DB saat menambahkan ulasan untuk produk "
            f"{id} oleh pengguna {user_id}: {service_err}",
            exc_info=True,
        )
        message: str = "Terjadi kesalahan saat menambahkan ulasan."
        if is_ajax:
            return (
                jsonify(
                    {"success": False, "message": "Terjadi kesalahan server."}
                ),
                500,
            )
        flash(message, "danger")
        return redirect(url_for("product.product_detail", id=id))

    except Exception as e:
        logger.error(
            "Kesalahan tak terduga saat menambahkan ulasan untuk produk "
            f"{id} oleh pengguna {user_id}: {e}",
            exc_info=True,
        )
        message = "Terjadi kesalahan tak terduga saat menambahkan ulasan."
        if is_ajax:
            return (
                jsonify(
                    {"success": False, "message": "Terjadi kesalahan server."}
                ),
                500,
            )
        flash(message, "danger")
        return redirect(url_for("product.product_detail", id=id))