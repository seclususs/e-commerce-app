from app.core.db import get_db_connection


class ReviewService:

    def get_reviews_for_product(self, product_id):
        conn = get_db_connection()
        reviews = conn.execute("SELECT r.*, u.username FROM reviews r JOIN users u ON r.user_id = u.id WHERE r.product_id = ? ORDER BY r.created_at DESC", (product_id,)).fetchall()
        conn.close()
        return [dict(r) for r in reviews]

    def get_review_by_id(self, review_id):
        conn = get_db_connection()
        review = conn.execute("SELECT r.*, u.username FROM reviews r JOIN users u ON r.user_id = u.id WHERE r.id = ?", (review_id,)).fetchone()
        conn.close()
        return dict(review) if review else None

    def check_user_can_review(self, user_id, product_id):
        conn = get_db_connection()
        try:
            has_purchased = conn.execute("SELECT 1 FROM orders o JOIN order_items oi ON o.id = oi.order_id WHERE o.user_id = ? AND oi.product_id = ? AND o.status = 'Selesai' LIMIT 1", (user_id, product_id)).fetchone()
            if has_purchased:
                has_reviewed = conn.execute('SELECT 1 FROM reviews WHERE user_id = ? AND product_id = ? LIMIT 1', (user_id, product_id)).fetchone()
                return not has_reviewed
            return False
        finally:
            conn.close()

    def add_review(self, user_id, product_id, rating, comment):
        if not self.check_user_can_review(user_id, product_id):
            return {'success': False, 'message': 'Anda hanya bisa memberi ulasan untuk produk yang sudah Anda beli dan selesaikan pesanannya.'}

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO reviews (product_id, user_id, rating, comment) VALUES (?, ?, ?, ?)', (product_id, user_id, rating, comment))
            new_id = cursor.lastrowid
            conn.commit()
            return {'success': True, 'message': 'Terima kasih atas ulasan Anda!', 'review_id': new_id}
        finally:
            conn.close()


review_service = ReviewService()