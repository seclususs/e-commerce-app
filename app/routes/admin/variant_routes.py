from flask import render_template, request, redirect, url_for, flash, jsonify
from app.core.db import get_content
from app.utils.route_decorators import admin_required
from app.services.products.product_query_service import product_query_service
from app.services.products.variant_service import variant_service
from app.utils.logging_utils import get_logger
from . import admin_bp

logger = get_logger(__name__)


@admin_bp.route('/product/<int:product_id>/variants', methods=['GET', 'POST'])
@admin_required
def manage_variants(product_id):
    if request.method == 'POST':
        action = request.form.get('action')
        logger.debug(
            f"Permintaan POST untuk mengelola varian produk dengan ID: {product_id}. "
            f"Aksi: {action}. Data form: {request.form.to_dict()}"
        )

        result = {'success': False, 'message': 'Aksi tidak valid'}
        status_code = 400

        try:
            if action == 'add':
                size = request.form.get('size')
                stock = request.form.get('stock')
                weight_grams = request.form.get('weight_grams')
                sku = request.form.get('sku')

                result = variant_service.add_variant(
                    product_id, size, stock, weight_grams, sku
                )

                if result.get('success'):
                    status_code = 200
                    html = render_template(
                        'admin/partials/_variant_row.html',
                        variant=result['data'],
                        product_id=product_id
                    )
                    result['html'] = html
                    logger.info(
                        f"Varian '{size}' berhasil ditambahkan untuk produk ID {product_id}."
                    )
                else:
                    logger.warning(
                        f"Gagal menambahkan varian untuk produk ID {product_id}. "
                        f"Alasan: {result.get('message')}"
                    )

            elif action == 'update':
                variant_id = request.form.get('variant_id')
                size = request.form.get('size')
                stock = request.form.get('stock')
                weight_grams = request.form.get('weight_grams')
                sku = request.form.get('sku')

                result = variant_service.update_variant(
                    product_id, variant_id, size, stock, weight_grams, sku
                )

                if result.get('success'):
                    status_code = 200
                    result['data'] = dict(request.form)
                    logger.info(
                        f"Varian ID {variant_id} berhasil diperbarui untuk produk ID {product_id}."
                    )
                else:
                    logger.warning(
                        f"Gagal memperbarui varian ID {variant_id}. "
                        f"Alasan: {result.get('message')}"
                    )

            return jsonify(result), status_code

        except Exception as e:
            logger.error(
                f"Terjadi kesalahan saat memproses aksi varian '{action}' untuk produk ID {product_id}: {e}",
                exc_info=True
            )
            return jsonify(
                {'success': False, 'message': 'Terjadi kesalahan pada server.'}
            ), 500

    logger.debug(f"Permintaan GET untuk mengelola varian produk dengan ID: {product_id}")

    try:
        product = product_query_service.get_product_by_id(product_id)

        if not product or not product['has_variants']:
            logger.warning(
                f"Produk dengan ID {product_id} tidak ditemukan atau tidak memiliki varian."
            )
            flash('Produk tidak ditemukan atau tidak memiliki varian.', 'danger')
            return redirect(url_for('admin.admin_products'))

        variants = variant_service.get_variants_for_product(product_id)
        logger.info(f"Berhasil mengambil {len(variants)} varian untuk produk ID {product_id}.")

        return render_template(
            'admin/manage_variants.html',
            product=product,
            variants=variants,
            content=get_content(),
            product_id=product_id
        )

    except Exception as e:
        logger.error(
            f"Terjadi kesalahan saat memuat halaman varian untuk produk ID {product_id}: {e}",
            exc_info=True
        )
        flash("Gagal memuat halaman varian.", "danger")
        return redirect(url_for('admin.admin_products'))


@admin_bp.route(
    '/product/<int:product_id>/variant/delete/<int:variant_id>',
    methods=['POST']
)
@admin_required
def delete_variant(product_id, variant_id):
    logger.debug(
        f"Mencoba menghapus varian dengan ID {variant_id} untuk produk ID {product_id}"
    )

    try:
        result = variant_service.delete_variant(product_id, variant_id)

        if result.get('success'):
            logger.info(f"Varian dengan ID {variant_id} berhasil dihapus.")
        else:
            logger.warning(
                f"Gagal menghapus varian dengan ID {variant_id}. "
                f"Alasan: {result.get('message')}"
            )

        return jsonify(result)

    except Exception as e:
        logger.error(
            f"Terjadi kesalahan saat menghapus varian ID {variant_id}: {e}",
            exc_info=True
        )
        return jsonify(
            {'success': False, 'message': 'Terjadi kesalahan pada server.'}
        ), 500