from app.core.db import get_db_connection
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ReviewService:
    
    
    def get_reviews_for_product(self, product_id):
        logger.debug(f"Mengambil ulasan untuk ID produk: {product_id}")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(
                """
                SELECT r.*, u.username
                FROM reviews r
                JOIN users u ON r.user_id = u.id
                WHERE r.product_id = %s
                ORDER BY r.created_at DESC
                """,
                (product_id,),
            )
            reviews = cursor.fetchall()
            logger.info(f"Mengambil {len(reviews)} ulasan untuk ID produk: {product_id}")
            return reviews

        except Exception as e:
            logger.error(f"Kesalahan saat mengambil ulasan untuk ID produk {product_id}: {e}", exc_info=True)
            raise

        finally:
            cursor.close()
            conn.close()
            logger.debug(f"Koneksi database ditutup untuk get_reviews_for_product {product_id}")


    def get_review_by_id(self, review_id):
        logger.debug(f"Mengambil ulasan berdasarkan ID: {review_id}")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(
                """
                SELECT r.*, u.username
                FROM reviews r
                JOIN users u ON r.user_id = u.id
                WHERE r.id = %s
                """,
                (review_id,),
            )
            review = cursor.fetchone()

            if review:
                logger.info(f"ID Ulasan {review_id} ditemukan.")
            else:
                logger.warning(f"ID Ulasan {review_id} tidak ditemukan.")

            return review if review else None

        except Exception as e:
            logger.error(f"Kesalahan saat mengambil ID ulasan {review_id}: {e}", exc_info=True)
            raise

        finally:
            cursor.close()
            conn.close()
            logger.debug(f"Koneksi database ditutup untuk get_review_by_id {review_id}")


    def check_user_can_review(self, user_id, product_id):
        logger.debug(f"Memeriksa apakah ID pengguna {user_id} dapat mengulas ID produk {product_id}")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(
                """
                SELECT 1
                FROM orders o
                JOIN order_items oi ON o.id = oi.order_id
                WHERE o.user_id = %s
                  AND oi.product_id = %s
                  AND o.status = 'Selesai'
                LIMIT 1
                """,
                (user_id, product_id),
            )
            has_purchased = cursor.fetchone()

            if has_purchased:
                cursor.execute(
                    "SELECT 1 FROM reviews WHERE user_id = %s AND product_id = %s LIMIT 1",
                    (user_id, product_id),
                )
                has_reviewed = cursor.fetchone()
                can_review = not has_reviewed
                logger.info(
                    f"Pengecekan ulasan untuk pengguna {user_id}, produk {product_id}: "
                    f"Dibeli=True, Diulas={bool(has_reviewed)}, BisaUlas={can_review}"
                )
                return can_review

            logger.info(
                f"Pengecekan ulasan untuk pengguna {user_id}, produk {product_id}: Dibeli=False, BisaUlas=False"
            )
            return False

        except Exception as e:
            logger.error(
                f"Kesalahan saat memeriksa izin ulasan untuk pengguna {user_id}, produk {product_id}: {e}",
                exc_info=True,
            )
            return False

        finally:
            cursor.close()
            conn.close()
            logger.debug(f"Koneksi database ditutup untuk check_user_can_review ({user_id}, {product_id})")


    def add_review(self, user_id, product_id, rating, comment):
        logger.debug(f"Mencoba menambahkan ulasan untuk produk {product_id} oleh pengguna {user_id}. Peringkat: {rating}")

        if not self.check_user_can_review(user_id, product_id):
            logger.warning(f"Penambahan ulasan gagal untuk pengguna {user_id}, produk {product_id}: Pengguna tidak dapat mengulas.")
            return {
                'success': False,
                'message': 'Anda hanya bisa memberi ulasan untuk produk yang sudah Anda beli dan selesaikan pesanannya.'
            }

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO reviews (product_id, user_id, rating, comment)
                VALUES (%s, %s, %s, %s)
                """,
                (product_id, user_id, rating, comment),
            )
            new_id = cursor.lastrowid
            conn.commit()
            logger.info(
                f"Ulasan berhasil ditambahkan untuk produk {product_id} oleh pengguna {user_id}. "
                f"ID ulasan baru: {new_id}"
            )
            return {'success': True, 'message': 'Terima kasih atas ulasan Anda!', 'review_id': new_id}

        except Exception as e:
            conn.rollback()
            logger.error(
                f"Kesalahan saat menambahkan ulasan untuk produk {product_id} oleh pengguna {user_id}: {e}",
                exc_info=True,
            )
            return {'success': False, 'message': 'Gagal menambahkan ulasan.'}

        finally:
            cursor.close()
            conn.close()
            logger.debug(f"Koneksi database ditutup untuk add_review ({user_id}, {product_id})")


review_service = ReviewService()