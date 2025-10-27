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
        existing_product: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[str], List[str], List[str], List[str], Optional[str]]:
        logger.debug("Menangani unggahan dan pemrosesan gambar.")

        new_images: List[Any] = (
            files.getlist("new_images")
            if existing_product
            else files.getlist("images")
        )
        
        saved_filenames: Dict[str, str] = {}

        for img in new_images:

            if img and img.filename:

                try:
                    saved_path: Optional[str] = save_compressed_image(img)

                    if saved_path:
                        saved_filenames[img.filename] = saved_path
                        logger.debug(
                            f"Menyimpan gambar baru: {img.filename} -> {saved_path}"
                        )
                    else:
                        logger.warning(
                            f"Gagal menyimpan gambar baru {img.filename}"
                        )

                except Exception as e:
                    logger.error(
                        f"Kesalahan menyimpan gambar {img.filename}: {e}",
                        exc_info=True,
                    )

        logger.debug(f"Peta nama file baru yang disimpan: {saved_filenames}")

        current_main: Optional[str] = None
        current_additional: List[str] = []
        all_current_images: List[str] = []
        images_marked_for_delete: List[str] = (
            form_data.getlist("delete_image") if existing_product else []
        )

        if existing_product:
            current_main = existing_product.get("image_url")
            additional_raw = (
                existing_product.get("additional_image_urls", "[]") or "[]"
            )

            loaded_additional: Any = None

            if isinstance(additional_raw, list):
                loaded_additional = additional_raw

            elif isinstance(additional_raw, str):

                try:
                    loaded_additional = json.loads(additional_raw)

                    if not isinstance(loaded_additional, list):
                        logger.warning(
                            f"additional_image_urls yang didekode bukan list untuk produk {existing_product.get('id')}: tipe {type(loaded_additional)}. Dianggap kosong."
                        )
                        loaded_additional = []

                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(
                        f"Tidak dapat mem-parsing JSON additional_image_urls yang ada untuk produk {existing_product.get('id')}: {e}. Raw: '{additional_raw}'. Dianggap kosong."
                    )
                    loaded_additional = []

            else:
                logger.warning(
                    f"Tipe tak terduga untuk additional_image_urls produk {existing_product.get('id')}: {type(additional_raw)}. Dianggap kosong."
                )
                loaded_additional = []

            current_additional = [
                str(item)
                for item in loaded_additional
                if item and isinstance(item, str)
            ]

            if current_main:
                all_current_images.append(current_main)

            all_current_images.extend(current_additional)
            all_current_images = list(set(filter(None, all_current_images)))

        logger.debug(
            f"Semua gambar saat ini (sebelum tanda hapus): {all_current_images}"
        )
        logger.debug(f"Gambar ditandai untuk dihapus: {images_marked_for_delete}")

        remaining_images: List[str] = [
            img
            for img in all_current_images
            if img not in images_marked_for_delete
        ]
        final_pool: List[str] = remaining_images + list(saved_filenames.values())
        final_pool = list(set(filter(None, final_pool)))
        logger.debug(f"Gambar yang tersisa: {remaining_images}")
        logger.debug(f"Kumpulan gambar akhir yang tersedia: {final_pool}")

        main_image_identifier: Optional[str] = form_data.get("main_image")
        final_main: Optional[str] = None
        logger.debug(f"Identifier gambar utama dari form: {main_image_identifier}")

        if main_image_identifier:

            if main_image_identifier in saved_filenames:
                potential_main = saved_filenames[main_image_identifier]

                if potential_main in final_pool:
                    final_main = potential_main
                    logger.debug(
                        f"Gambar utama yang dipilih adalah unggahan baru: {main_image_identifier} -> {final_main}"
                    )
                else:
                    logger.warning(
                        f"Identifier gambar utama '{main_image_identifier}' (baru) mengarah ke '{potential_main}' tetapi tidak ditemukan di kumpulan akhir {final_pool}. Perlu fallback."
                    )

            elif main_image_identifier in remaining_images:
                final_main = main_image_identifier
                logger.debug(
                    f"Gambar utama yang dipilih adalah gambar yang sudah ada: {final_main}"
                )
            else:
                logger.warning(
                    f"Identifier gambar utama '{main_image_identifier}' bukan nama gambar baru yang valid dan tidak ada di gambar tersisa {remaining_images}. Perlu fallback."
                )
        else:
            logger.debug("Tidak ada identifier gambar utama yang dikirim dalam form.")

        if not final_main and final_pool:
            final_main = final_pool[0]
            logger.info(
                f"Fallback: Mengatur gambar utama ke yang pertama tersedia: {final_main}"
            )

        elif not final_pool:
            logger.error(
                "Pemrosesan gambar gagal: Tidak ada gambar tersisa setelah penghapusan dan penambahan."
            )
            images_physically_deleted: List[str] = self._delete_image_files(
                images_marked_for_delete, all_current_images
            )
            return (
                None,
                [],
                images_physically_deleted,
                images_marked_for_delete,
                "Produk harus memiliki setidaknya satu gambar.",
            )

        logger.info(f"Gambar utama akhir yang ditentukan: {final_main}")

        final_additional: List[str] = [
            img for img in final_pool if img != final_main
        ]
        logger.debug(f"Gambar tambahan akhir: {final_additional}")

        images_physically_deleted: List[str] = self._delete_image_files(
            images_marked_for_delete, all_current_images
        )
        logger.info(f"Gambar yang dihapus secara fisik: {images_physically_deleted}")

        return (
            final_main,
            final_additional,
            images_physically_deleted,
            images_marked_for_delete,
            None,
        )


    def _delete_image_files(
        self,
        images_marked_for_delete: List[str],
        all_existing_images: List[str],
    ) -> List[str]:
        deleted_files: List[str] = []
        image_folder: str = current_app.config["IMAGE_FOLDER"]

        files_to_attempt_delete = [
            img
            for img in images_marked_for_delete
            if img in all_existing_images
        ]

        if not files_to_attempt_delete:
            return []

        logger.debug(
            f"Mencoba penghapusan fisik file gambar: {files_to_attempt_delete}"
        )

        for img_file in files_to_attempt_delete:

            if not img_file or not isinstance(img_file, str):
                logger.warning(
                    f"Melewati nama file gambar tidak valid untuk dihapus: {img_file}"
                )
                continue

            try:
                if ".." in img_file or img_file.startswith("/"):
                    logger.warning(
                        f"Nama file tidak valid untuk dihapus (upaya traversal path?): {img_file}"
                    )
                    continue

                file_path: str = os.path.join(image_folder, img_file)

                if os.path.isfile(file_path):
                    os.remove(file_path)
                    deleted_files.append(img_file)
                    logger.info(f"File gambar fisik dihapus: {img_file}")
                else:
                    logger.warning(
                        f"File gambar tidak ditemukan untuk dihapus (sudah dihapus atau tidak valid?): {img_file} di path {file_path}"
                    )

            except OSError as e:
                logger.error(
                    f"Kesalahan OS saat menghapus file gambar {img_file}: {e}",
                    exc_info=True,
                )

            except Exception as e:
                logger.error(
                    f"Kesalahan tak terduga saat menghapus file gambar {img_file}: {e}",
                    exc_info=True,
                )

        logger.info(
            f"Jumlah file gambar yang dihapus secara fisik: {len(deleted_files)}"
        )
        return deleted_files


    def delete_all_product_images(
        self, product: Optional[Dict[str, Any]]
    ) -> List[str]:
        images_to_delete: List[str] = []
        product_id_log = product.get("id", "N/A") if product else "N/A"

        if product:
            main_image = product.get("image_url")

            if main_image and isinstance(main_image, str):
                images_to_delete.append(main_image)

            additional_raw: Any = product.get("additional_image_urls")
            additional_images: List[str] = []

            if isinstance(additional_raw, list):
                loaded_additional = additional_raw

            elif isinstance(additional_raw, str) and additional_raw.strip():

                try:
                    loaded_additional = json.loads(additional_raw)

                    if not isinstance(loaded_additional, list):
                        logger.warning(
                            f"additional_image_urls yang didekode bukan list saat penghapusan penuh untuk produk {product_id_log}: tipe {type(loaded_additional)}. Diabaikan."
                        )
                        loaded_additional = []

                except (json.JSONDecodeError, TypeError):
                    logger.warning(
                        f"Tidak dapat mem-parsing JSON additional_image_urls saat penghapusan penuh untuk produk {product_id_log}: {additional_raw}. Diabaikan."
                    )
                    loaded_additional = []

            else:
                loaded_additional = []

            additional_images = [
                str(item)
                for item in loaded_additional
                if item and isinstance(item, str)
            ]

            if additional_images:
                images_to_delete.extend(additional_images)

        images_to_delete = list(set(filter(None, images_to_delete)))
        logger.debug(
            f"Mencoba menghapus semua gambar untuk produk yang dihapus (ID: {product_id_log}): {images_to_delete}"
        )

        return self._delete_image_files(images_to_delete, images_to_delete)

image_service = ImageService()