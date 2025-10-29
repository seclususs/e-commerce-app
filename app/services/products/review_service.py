from typing import Any, Dict, List, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection

from app.core.db import get_db_connection
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError
from app.repository.review_repository import (
    ReviewRepository, review_repository
)


class ReviewService:

    def __init__(self, review_repo: ReviewRepository = review_repository):
        self.review_repository = review_repo


    def get_reviews_for_product(
        self, product_id: Any
    ) -> List[Dict[str, Any]]:
        
        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            reviews: List[Dict[str, Any]] = (
                self.review_repository.find_by_product_id_with_user(
                    conn, product_id
                )
            )
            return reviews
        
        except mysql.connector.Error as e:
            raise DatabaseException(
                f"Kesalahan database saat mengambil ulasan: {e}"
            )
        
        except Exception as e:
            raise ServiceLogicError(
                f"Kesalahan layanan saat mengambil ulasan: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def get_review_by_id(
        self, review_id: Any
    ) -> Optional[Dict[str, Any]]:
        
        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            review: Optional[Dict[str, Any]] = (
                self.review_repository.find_by_id_with_user(conn, review_id)
            )
            return review if review else None
        
        except mysql.connector.Error as e:
            raise DatabaseException(
                f"Kesalahan database saat mengambil ulasan: {e}"
            )
        
        except Exception as e:
            raise ServiceLogicError(
                f"Kesalahan layanan saat mengambil ulasan: {e}"
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()


    def check_user_can_review(
        self,
        user_id: Any,
        product_id: Any,
        conn: Optional[MySQLConnection] = None,
    ) -> bool:
        
        close_conn: bool = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True

        try:
            has_purchased: bool = (
                self.review_repository.check_user_purchase(
                    conn, user_id, product_id
                )
            )
            if has_purchased:
                has_reviewed: bool = (
                    self.review_repository.check_user_review_exists(
                        conn, user_id, product_id
                    )
                )
                can_review: bool = not has_reviewed
                return can_review
            return False
        
        except mysql.connector.Error as e:
            raise DatabaseException(
                f"Kesalahan database saat memeriksa izin ulasan: {e}"
            )
        
        except Exception as e:
            raise ServiceLogicError(
                f"Kesalahan layanan saat memeriksa izin ulasan: {e}"
            )
        
        finally:
            if close_conn and conn and conn.is_connected():
                conn.close()


    def add_review(
        self, user_id: Any, product_id: Any, rating: Any, comment: str
    ) -> Dict[str, Any]:
        
        if not rating or not comment or not comment.strip():
            raise ValidationError("Rating dan komentar tidak boleh kosong.")

        conn: Optional[MySQLConnection] = None
        try:
            conn = get_db_connection()
            can_review: bool = self.check_user_can_review(
                user_id, product_id, conn
            )
            if not can_review:
                return {
                    "success": False,
                    "message": "Anda hanya bisa memberi ulasan untuk produk yang sudah Anda beli dan selesaikan pesanannya.",
                }
            new_id: int = self.review_repository.create(
                conn, user_id, product_id, rating, comment
            )
            conn.commit()
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
            raise DatabaseException(
                "Gagal menambahkan ulasan karena kesalahan database."
            )
        
        except Exception as e:
            if conn and conn.is_connected():
                conn.rollback()
            raise ServiceLogicError(
                "Gagal menambahkan ulasan karena kesalahan server."
            )
        
        finally:
            if conn and conn.is_connected():
                conn.close()

review_service = ReviewService(review_repository)