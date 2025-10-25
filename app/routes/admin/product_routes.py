from flask import render_template, request, redirect, url_for, flash, jsonify
from app.core.db import get_content
from app.utils.route_decorators import admin_required
from app.services.products.product_service import product_service
from app.services.products.product_query_service import product_query_service
from app.services.products.product_bulk_service import product_bulk_service
from app.services.products.category_service import category_service
from app.utils.logging_utils import get_logger
from . import admin_bp

logger = get_logger(__name__)


@admin_bp.route('/products', methods=['GET', 'POST'])
@admin_required
def admin_products():
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        logger.debug(f"Permintaan POST ke /products. Jenis form: {form_type}")

        try:
            if form_type == 'bulk_action':
                action = request.form.get('bulk_action')
                selected_ids = request.form.getlist('product_ids')
                category_id = request.form.get('bulk_category_id')
                logger.info(
                    f"Menjalankan aksi massal: {action} pada produk dengan ID: {selected_ids}. "
                    f"Kategori ID: {category_id}"
                )

                result = product_bulk_service.handle_bulk_product_action(
                    action, selected_ids, category_id
                )

                if result.get('success'):
                    result['ids'] = selected_ids
                    result['action'] = action
                    if action == 'set_category' and category_id:
                        category = category_service.get_category_by_id(category_id)
                        result['new_category_name'] = category['name'] if category else 'Tidak diketahui'
                    logger.info(
                        f"Aksi massal '{action}' berhasil dijalankan. Pesan: {result['message']}"
                    )
                    return jsonify(result)

                logger.warning(
                    f"Aksi massal '{action}' gagal dijalankan. Alasan: {result['message']}"
                )
                return jsonify(result), 400

            if form_type == 'add_product':
                logger.info("Menambahkan produk baru.")
                result = product_service.create_product(request.form, request.files)

                if result.get('success'):
                    flash(result.get('message', 'Produk berhasil ditambahkan!'), 'success')
                    logger.info(
                        f"Produk '{request.form.get('name')}' berhasil ditambahkan."
                    )
                else:
                    flash(result.get('message', 'Gagal menambahkan produk.'), 'danger')
                    logger.warning(
                        f"Gagal menambahkan produk '{request.form.get('name')}'. "
                        f"Alasan: {result.get('message')}"
                    )
                return redirect(url_for('admin.admin_products'))

            logger.warning(f"Jenis form tidak dikenal dikirimkan: {form_type}")
            flash("Jenis form tidak dikenal.", "danger")
            return redirect(url_for('admin.admin_products'))

        except Exception as e:
            logger.error(
                f"Kesalahan saat memproses permintaan POST untuk form_type '{form_type}': {e}",
                exc_info=True
            )
            if form_type == 'bulk_action':
                return (
                    jsonify({'success': False, 'message': 'Terjadi kesalahan pada server.'}),
                    500,
                )
            flash("Terjadi kesalahan server saat memproses permintaan.", "danger")
            return redirect(url_for('admin.admin_products'))
        
    search_term = request.args.get('search', '').strip()
    category_filter = request.args.get('category')
    stock_status_filter = request.args.get('stock_status')
    logger.debug(
        f"Mengambil daftar produk dengan filter - Pencarian: {search_term}, "
        f"Kategori: {category_filter}, Status Stok: {stock_status_filter}"
    )

    try:
        products = product_query_service.get_all_products_with_category(
            search=search_term,
            category_id=category_filter,
            stock_status=stock_status_filter,
        )
        logger.info(f"Berhasil mengambil {len(products)} produk sesuai filter.")

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            logger.debug("Mengembalikan respon JSON untuk permintaan filter produk AJAX.")
            html = render_template(
                'admin/partials/_product_table_body.html',
                products=products
            )
            return jsonify({'success': True, 'html': html})

        categories = category_service.get_all_categories()
        logger.info("Menampilkan halaman kelola produk.")
        return render_template(
            'admin/manage_products.html',
            products=products,
            categories=categories,
            content=get_content(),
            search_term=search_term,
        )

    except Exception as e:
        logger.error(
            f"Kesalahan saat mengambil data produk atau kategori: {e}",
            exc_info=True
        )
        flash("Gagal memuat daftar produk atau kategori.", "danger")
        return render_template(
            'admin/manage_products.html',
            products=[],
            categories=[],
            content=get_content(),
            search_term=search_term,
        )


@admin_bp.route('/edit_product/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(id):
    if request.method == 'POST':
        logger.debug(f"Mencoba memperbarui produk dengan ID: {id}")
        try:
            result = product_service.update_product(id, request.form, request.files)
            if result.get('success'):
                result['redirect_url'] = url_for('admin.admin_products')
                logger.info(f"Produk dengan ID {id} berhasil diperbarui.")
                return jsonify(result)

            logger.warning(
                f"Gagal memperbarui produk ID {id}. Alasan: {result['message']}"
            )
            return jsonify(result), 400

        except Exception as e:
            logger.error(
                f"Kesalahan saat memperbarui produk ID {id}: {e}",
                exc_info=True
            )
            return jsonify({
                'success': False,
                'message': 'Terjadi kesalahan server saat memperbarui produk.',
            }), 500
        
    logger.debug(f"Mengambil detail produk untuk diedit. ID Produk: {id}")
    try:
        product = product_query_service.get_product_by_id(id)
        if not product:
            logger.warning(f"Produk dengan ID {id} tidak ditemukan untuk diedit.")
            flash('Produk tidak ditemukan.', 'danger')
            return redirect(url_for('admin.admin_products'))

        categories = category_service.get_all_categories()
        additional_images = product.get('additional_image_urls', [])
        logger.info(
            f"Detail produk berhasil diambil untuk ID {id}. "
            f"Nama: {product.get('name')}"
        )
        return render_template(
            'admin/product_editor.html',
            product=product,
            additional_images=additional_images,
            categories=categories,
            content=get_content(),
        )

    except Exception as e:
        logger.error(
            f"Kesalahan saat mengambil detail produk ID {id}: {e}",
            exc_info=True
        )
        flash("Gagal memuat detail produk.", "danger")
        return redirect(url_for('admin.admin_products'))


@admin_bp.route('/delete_product/<int:id>', methods=['POST'])
@admin_required
def delete_product(id):
    logger.debug(f"Mencoba menghapus produk dengan ID: {id}")
    try:
        result = product_service.delete_product(id)
        if result.get('success'):
            logger.info(f"Produk dengan ID {id} berhasil dihapus.")
        else:
            logger.warning(
                f"Gagal menghapus produk ID {id}. Alasan: {result.get('message')}"
            )
        return jsonify(result)

    except Exception as e:
        logger.error(
            f"Kesalahan saat menghapus produk ID {id}: {e}",
            exc_info=True
        )
        return jsonify({
            'success': False,
            'message': 'Terjadi kesalahan server saat menghapus produk.',
        }), 500