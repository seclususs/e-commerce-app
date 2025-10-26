from typing import Any, Dict, List, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.core.db import get_db_connection
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ReviewService:

    def get_reviews_for_product(
        self, product_id: Any
    ) -> List[Dict[str, Any]]:
        logger.debug(f"Mengambil ulasan untuk ID produk: {product_id}")

        conn: Optional[MySQLConnection] = None
        cursor: Optional[Any] = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

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

            reviews: List[Dict[str, Any]] = cursor.fetchall()

            logger.info(
                f"Mengambil {len(reviews)} ulasan untuk ID produk: {product_id}"
            )
            
            return reviews
        
        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat mengambil ulasan {product_id}: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat mengambil ulasan: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat mengambil ulasan untuk ID produk {product_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat mengambil ulasan: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk get_reviews_for_product {product_id}"
            )


    def get_review_by_id(
        self, review_id: Any
    ) -> Optional[Dict[str, Any]]:
        logger.debug(f"Mengambil ulasan berdasarkan ID: {review_id}")
        conn: Optional[MySQLConnection] = None
        cursor: Optional[Any] = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT r.*, u.username
                FROM reviews r
                JOIN users u ON r.user_id = u.id
                WHERE r.id = %s
                """,
                (review_id,),
            )
            review: Optional[Dict[str, Any]] = cursor.fetchone()
            if review:
                logger.info(f"ID Ulasan {review_id} ditemukan.")
            else:
                logger.warning(f"ID Ulasan {review_id} tidak ditemukan.")
            return review if review else None
        
        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat mengambil ulasan {review_id}: {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat mengambil ulasan: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat mengambil ID ulasan {review_id}: {e}",
                exc_info=True
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat mengambil ulasan: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk get_review_by_id {review_id}"
            )


    def check_user_can_review(
        self,
        user_id: Any,
        product_id: Any,
        conn: Optional[MySQLConnection] = None
    ) -> bool:
        logger.debug(
            f"Memeriksa apakah ID pengguna {user_id} dapat mengulas ID produk {product_id}"
        )
        close_conn: bool = False
        cursor: Optional[Any] = None

        if conn is None:
            conn = get_db_connection()
            close_conn = True

        try:
            cursor = conn.cursor(dictionary=True)
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
            has_purchased: Optional[Dict[str, Any]] = cursor.fetchone()
            if has_purchased:
                cursor.execute(
                    "SELECT 1 FROM reviews WHERE user_id = %s AND product_id = %s LIMIT 1",
                    (user_id, product_id),
                )
                has_reviewed: Optional[Dict[str, Any]] = cursor.fetchone()
                can_review: bool = not has_reviewed
                logger.info(
                    f"Pengecekan ulasan untuk pengguna {user_id}, produk {product_id}: "
                    f"Dibeli=True, Diulas={bool(has_reviewed)}, BisaUlas={can_review}"
                )
                return can_review
            logger.info(
                f"Pengecekan ulasan untuk pengguna {user_id}, produk {product_id}: Dibeli=False, BisaUlas=False"
            )
            return False
        
        except mysql.connector.Error as e:
            logger.error(
                f"Kesalahan database saat memeriksa izin ulasan ({user_id}, {product_id}): {e}",
                exc_info=True,
            )
            raise DatabaseException(
                f"Kesalahan database saat memeriksa izin ulasan: {e}"
            )
        
        except Exception as e:
            logger.error(
                f"Kesalahan saat memeriksa izin ulasan untuk pengguna {user_id}, produk {product_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                f"Kesalahan layanan saat memeriksa izin ulasan: {e}"
            )
        
        finally:
            if cursor:
                cursor.close()
            if close_conn and conn and conn.is_connected():
                conn.close()
                logger.debug(
                    f"Koneksi database ditutup untuk check_user_can_review ({user_id}, {product_id})"
                )


    def add_review(
        self, user_id: Any, product_id: Any, rating: Any, comment: str
    ) -> Dict[str, Any]:
        logger.debug(
            f"Mencoba menambahkan ulasan untuk produk {product_id} oleh pengguna {user_id}. Peringkat: {rating}"
        )

        if not rating or not comment or not comment.strip():
            raise ValidationError("Rating dan komentar tidak boleh kosong.")

        conn: Optional[MySQLConnection] = None
        cursor: Optional[Any] = None

        try:
            conn = get_db_connection()
            can_review: bool = self.check_user_can_review(
                user_id, product_id, conn
            )
            if not can_review:
                logger.warning(
                    f"Penambahan ulasan gagal untuk pengguna {user_id}, produk {product_id}: Pengguna tidak dapat mengulas."
                )
                return {
                    "success": False,
                    "message": "Anda hanya bisa memberi ulasan untuk produk yang sudah Anda beli dan selesaikan pesanannya.",
                }
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO reviews (product_id, user_id, rating, comment)
                VALUES (%s, %s, %s, %s)
                """,
                (product_id, user_id, int(rating), comment.strip()),
            )
            new_id: int = cursor.lastrowid
            conn.commit()
            logger.info(
                f"Ulasan berhasil ditambahkan untuk produk {product_id} oleh pengguna {user_id}. "
                f"ID ulasan baru: {new_id}"
            )
            return {
                "success": True,
                "message": "Terima kasih atas ulasan Anda!",
                "review_id": new_id,
            }
        
        except ValueError:
            raise ValidationError("Rating harus berupa angka.")
        
        except mysql.connector.Error as db_err:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan DB saat menambahkan ulasan: {db_err}", exc_info=True
            )
            raise DatabaseException(
                "Gagal menambahkan ulasan karena kesalahan database."
            )
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            logger.error(
                f"Kesalahan saat menambahkan ulasan untuk produk {product_id} oleh pengguna {user_id}: {e}",
                exc_info=True,
            )
            raise ServiceLogicError(
                "Gagal menambahkan ulasan karena kesalahan server."
            )
        
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()
            logger.debug(
                f"Koneksi database ditutup untuk add_review ({user_id}, {product_id})"
            )

review_service = ReviewService()