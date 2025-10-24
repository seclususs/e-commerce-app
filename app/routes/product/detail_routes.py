from flask import render_template, request, session, redirect, url_for, flash, jsonify
from app.core.db import get_content
from app.services.products.product_query_service import product_query_service
from app.services.products.review_service import review_service
from app.utils.route_decorators import login_required
from app.utils.logging_utils import get_logger
from . import product_bp

logger = get_logger(__name__)


@product_bp.route('/product/<int:id>')
def product_detail(id):
    logger.debug(f"Mengambil halaman detail produk untuk ID: {id}")

    try:
        product = product_query_service.get_product_by_id(id)

        if product is None:
            logger.warning(f"Produk dengan ID {id} tidak ditemukan.")
            flash("Produk tidak ditemukan.", "danger")
            return redirect(url_for('product.products_page'))

        reviews = review_service.get_reviews_for_product(id)
        logger.info(f"Berhasil mengambil {len(reviews)} ulasan untuk produk ID {id}.")
        related_products = []

        category_id = product.get('category_id')
        if category_id:
            related_products = product_query_service.get_related_products(id, category_id)
            logger.info(f"Berhasil mengambil {len(related_products)} produk terkait.")

        user_id = session.get('user_id')
        can_review = False

        if user_id:
            can_review = review_service.check_user_can_review(user_id, id)
            logger.debug(f"Pengguna {user_id} dapat memberi ulasan untuk produk {id}: {can_review}")

        return render_template(
            'public/product_detail.html',
            product=product,
            reviews=reviews,
            related_products=related_products,
            content=get_content(),
            can_review=can_review
        )

    except Exception as e:
        logger.error(
            f"Kesalahan saat memuat halaman detail produk untuk ID {id}: {e}",
            exc_info=True
        )
        flash("Gagal memuat detail produk.", "danger")
        return redirect(url_for('product.products_page'))


@product_bp.route('/product/<int:id>/add_review', methods=['POST'])
@login_required
def add_review(id):
    rating = request.form.get('rating')
    comment = request.form.get('comment')
    user_id = session['user_id']

    logger.debug(
        f"Pengguna {user_id} mencoba menambahkan ulasan untuk produk {id}. "
        f"Rating: {rating}"
    )

    if not rating or not comment:
        logger.warning(
            f"Gagal menambahkan ulasan untuk produk {id} oleh pengguna {user_id}: "
            f"Rating atau komentar tidak diisi."
        )
        flash('Rating dan komentar tidak boleh kosong.', 'danger')
        return redirect(url_for('product.product_detail', id=id))

    try:
        result = review_service.add_review(user_id, id, rating, comment)
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if is_ajax:
            if result.get('success'):
                logger.info(
                    f"Ulasan berhasil ditambahkan melalui AJAX untuk produk {id} "
                    f"oleh pengguna {user_id}."
                )
                new_review = review_service.get_review_by_id(result['review_id'])
                review_html = render_template(
                    'partials/_review.html',
                    review=new_review
                )
                return jsonify({
                    'success': True,
                    'message': result['message'],
                    'review_html': review_html
                })
            else:
                logger.warning(
                    f"Gagal menambahkan ulasan melalui AJAX untuk produk {id} oleh pengguna "
                    f"{user_id}. Alasan: {result['message']}"
                )
                return jsonify({
                    'success': False,
                    'message': result['message']
                }), 400

        flash(
            result['message'],
            'success' if result['success'] else 'danger'
        )

        if result['success']:
            logger.info(
                f"Ulasan berhasil ditambahkan untuk produk {id} oleh pengguna {user_id}."
            )
        else:
            logger.warning(
                f"Gagal menambahkan ulasan untuk produk {id} oleh pengguna {user_id}. "
                f"Alasan: {result['message']}"
            )

        return redirect(url_for('product.product_detail', id=id))

    except Exception as e:
        logger.error(
            f"Kesalahan saat menambahkan ulasan untuk produk {id} oleh pengguna {user_id}: {e}",
            exc_info=True
        )
        flash('Terjadi kesalahan saat menambahkan ulasan.', 'danger')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': 'Terjadi kesalahan server.'
            }), 500

        return redirect(url_for('product.product_detail', id=id))