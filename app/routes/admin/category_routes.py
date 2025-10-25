from flask import render_template, request, redirect, url_for, flash, jsonify
from app.core.db import get_content
from app.utils.route_decorators import admin_required
from app.services.products.category_service import category_service
from app.utils.logging_utils import get_logger
from . import admin_bp

logger = get_logger(__name__)


@admin_bp.route('/categories', methods=['GET', 'POST'])
@admin_required
def admin_categories():
    if request.method == 'POST':
        action = request.form.get('action')
        name = request.form.get('name')
        category_id = request.form.get('id')

        logger.debug(
            f"Permintaan POST ke /categories. Aksi: {action}, "
            f"Nama: {name}, ID: {category_id}"
        )

        result = {'success': False, 'message': 'Aksi tidak valid.'}
        status_code = 400

        try:
            if action == 'add' and name:
                result = category_service.create_category(name)
                if result.get('success'):
                    html = render_template(
                        'admin/partials/_category_row.html',
                        category=result['data']
                    )
                    result['html'] = html
                    status_code = 200
                    logger.info(
                        f"Kategori '{name}' berhasil ditambahkan via service. "
                        f"ID: {result['data']['id']}"
                    )
                else:
                    logger.warning(
                        f"Gagal menambahkan kategori '{name}' via service. "
                        f"Alasan: {result.get('message')}"
                    )

            elif action == 'edit' and name and category_id:
                result = category_service.update_category(category_id, name)
                if result.get('success'):
                    result['data'] = {
                        'id': category_id,
                        'name': name
                    }
                    status_code = 200
                    logger.info(
                        f"Kategori dengan ID {category_id} "
                        f"berhasil diperbarui menjadi '{name}' via service."
                    )
                else:
                    logger.warning(
                        f"Gagal memperbarui kategori ID {category_id} via service. "
                        f"Alasan: {result.get('message')}"
                    )
            
            return jsonify(result), status_code

        except Exception as e:
            logger.error(
                f"Terjadi kesalahan saat memproses aksi kategori '{action}': {e}",
                exc_info=True
            )
            return jsonify(
                {'success': False, 'message': 'Terjadi kesalahan pada server.'}
            ), 500

    logger.debug("Permintaan GET ke /categories. Mengambil daftar kategori.")

    try:
        categories = category_service.get_all_categories()
        logger.info(f"Berhasil mengambil {len(categories)} kategori.")

        return render_template(
            'admin/manage_categories.html',
            categories=categories,
            content=get_content()
        )

    except Exception as e:
        logger.error(
            f"Terjadi kesalahan saat mengambil daftar kategori: {e}",
            exc_info=True
        )
        flash('Gagal memuat daftar kategori.', 'danger')

        return render_template(
            'admin/manage_categories.html',
            categories=[],
            content=get_content()
        )


@admin_bp.route('/delete_category/<int:id>', methods=['POST'])
@admin_required
def delete_category(id):
    logger.debug(f"Mencoba menghapus kategori dengan ID: {id}")

    try:
        result = category_service.delete_category(id)

        if result.get('success'):
            logger.info(f"Kategori dengan ID {id} berhasil dihapus via service.")
        else:
            logger.warning(
                f"Gagal menghapus kategori dengan ID {id} via service. "
                f"Alasan: {result.get('message')}"
            )

        return jsonify(result)

    except Exception as e:
        logger.error(
            f"Terjadi kesalahan saat menghapus kategori dengan ID {id}: {e}",
            exc_info=True
        )
        return jsonify(
            {'success': False, 'message': 'Terjadi kesalahan pada server.'}
        ), 500