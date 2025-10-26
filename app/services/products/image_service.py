import json
import os
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app

from app.utils.image_utils import save_compressed_image
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ImageService:

    def handle_image_upload(
        self,
        files: Any,
        form_data: Any,
        existing_product: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[str], List[str], List[str], List[str], Optional[str]]:
        logger.debug("Menangani unggahan dan pemrosesan gambar.")

        new_images: List[Any] = (
            files.getlist("new_images")
            if existing_product
            else files.getlist("images")
        )
        main_image_identifier: Optional[str] = form_data.get("main_image")
        images_to_delete: List[str] = (
            form_data.getlist("delete_image") if existing_product else []
        )
        saved_filenames: Dict[str, str] = {}

        for img in new_images:

            if img and img.filename:
                saved_path: Optional[str] = save_compressed_image(img)

                if saved_path:
                    saved_filenames[img.filename] = saved_path

                else:
                    logger.warning(f"Gagal menyimpan gambar {img.filename}")

        logger.debug(f"Nama file baru yang disimpan: {saved_filenames}")

        current_main: Optional[str] = None
        current_additional: List[str] = []

        if existing_product:
            current_main = existing_product.get("image_url")

            try:
                current_additional = json.loads(
                    existing_product.get("additional_image_urls", "[]") or "[]"
                )
            except (json.JSONDecodeError, TypeError):
                current_additional = []
                logger.warning(
                    f"Tidak dapat mengurai gambar tambahan yang ada untuk produk {existing_product.get('id')}"
                )

        all_current_images: List[str] = (
            ([current_main] + current_additional)
            if current_main
            else current_additional
        )
        remaining_images: List[str] = [
            img for img in all_current_images if img not in images_to_delete
        ]
        final_pool: List[str] = remaining_images + list(
            saved_filenames.values()
        )

        if not final_pool:
            logger.warning(
                "Pemrosesan gambar gagal: Tidak ada gambar yang tersisa."
            )
            return (
                None,
                None,
                [],
                images_to_delete,
                "Produk harus memiliki setidaknya satu gambar.",
            )
        
        final_main: Optional[str] = None
        if main_image_identifier:
            if main_image_identifier in saved_filenames:
                final_main = saved_filenames[main_image_identifier]
            elif main_image_identifier in remaining_images:
                final_main = main_image_identifier

        if not final_main:
            final_main = final_pool[0]

        final_additional: List[str] = [
            img for img in final_pool if img != final_main
        ]
        images_physically_deleted: List[str] = self._delete_image_files(
            images_to_delete, all_current_images
        )
        logger.info(
            f"Pemrosesan gambar selesai. Utama: {final_main}, "
            f"Tambahan: {len(final_additional)}, "
            f"Dihapus: {len(images_physically_deleted)}"
        )

        return (
            final_main,
            final_additional,
            images_physically_deleted,
            images_to_delete,
            None,
        )


    def _delete_image_files(
        self,
        images_marked_for_delete: List[str],
        all_existing_images: List[str]
    ) -> List[str]:
        deleted_files: List[str] = []
        image_folder: str = current_app.config["IMAGE_FOLDER"]

        for img_file in images_marked_for_delete:

            if img_file in all_existing_images:

                try:
                    file_path: str = os.path.join(image_folder, img_file)

                    if os.path.exists(file_path):
                        os.remove(file_path)
                        deleted_files.append(img_file)
                        logger.info(f"File gambar dihapus: {img_file}")

                    else:
                        logger.warning(
                            f"File gambar tidak ditemukan untuk dihapus: {img_file}"
                        )

                except OSError as e:
                    logger.error(
                        f"Kesalahan saat menghapus file gambar {img_file}: {e}",
                        exc_info=True
                    )

        return deleted_files


    def delete_all_product_images(
        self, product: Optional[Dict[str, Any]]
    ) -> List[str]:
        images_to_delete: List[str] = []

        if product:

            if product.get("image_url"):
                images_to_delete.append(product.get("image_url"))

            additional_raw: Optional[str] = product.get(
                "additional_image_urls"
            )

            if additional_raw:

                try:
                    additional: List[str] = json.loads(additional_raw)
                    if isinstance(additional, list):
                        images_to_delete.extend(additional)

                except (json.JSONDecodeError, TypeError):
                    logger.warning(
                        f"Tidak dapat mengurai additional_image_urls untuk produk yang dihapus {product.get('id')}"
                    )

        images_to_delete = [img for img in images_to_delete if img]
        
        logger.debug(
            f"Mencoba menghapus semua gambar untuk produk: {images_to_delete}"
        )

        return self._delete_image_files(images_to_delete, images_to_delete)

image_service = ImageService()