from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock

from app.services.products.review_service import ReviewService
from app.exceptions.api_exceptions import ValidationError


class TestReviewService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_review_repo = MagicMock()
        
        self.review_service = ReviewService(
            review_repo=self.mock_review_repo
        )

    def tearDown(self):
        super().tearDown()

    def test_get_reviews_for_product_success(self):
        mock_reviews = [{"id": 1, "comment": "Great!"}]
        (
            self.mock_review_repo.
            find_by_product_id_with_user.return_value
        ) = mock_reviews
        
        result = self.review_service.get_reviews_for_product(1)
        
        self.assertEqual(result, mock_reviews)

    def test_get_review_by_id_success(self):
        mock_review = {"id": 1, "comment": "Great!"}
        self.mock_review_repo.find_by_id_with_user.return_value = mock_review
        
        result = self.review_service.get_review_by_id(1)
        
        self.assertEqual(result, mock_review)

    def test_check_user_can_review_true(self):
        self.mock_review_repo.check_user_purchase.return_value = True
        self.mock_review_repo.check_user_review_exists.return_value = False
        
        result = self.review_service.check_user_can_review(1, 1)
        
        self.assertTrue(result)

    def test_check_user_can_review_false_not_purchased(self):
        self.mock_review_repo.check_user_purchase.return_value = False
        
        result = self.review_service.check_user_can_review(1, 1)
        
        self.assertFalse(result)
        self.mock_review_repo.check_user_review_exists.assert_not_called()

    def test_check_user_can_review_false_already_reviewed(self):
        self.mock_review_repo.check_user_purchase.return_value = True
        self.mock_review_repo.check_user_review_exists.return_value = True
        
        result = self.review_service.check_user_can_review(1, 1)

        self.assertFalse(result)

    def test_add_review_success(self):
        self.mock_review_repo.check_user_purchase.return_value = True
        self.mock_review_repo.check_user_review_exists.return_value = False
        self.mock_review_repo.create.return_value = 1
        
        result = self.review_service.add_review(1, 1, 5, "Great")
        
        self.mock_review_repo.create.assert_called_once_with(
            self.db_conn, 1, 1, 5, "Great"
        )
        self.assertEqual(result, {
            "success": True,
            "message": "Terima kasih atas ulasan Anda!",
            "review_id": 1
        })

    def test_add_review_cannot_review(self):
        self.mock_review_repo.check_user_purchase.return_value = False
        
        result = self.review_service.add_review(1, 1, 5, "Great")
        
        self.mock_review_repo.create.assert_not_called()
        self.assertEqual(result["success"], False)
        self.assertIn("hanya bisa", result["message"])

    def test_add_review_validation_error(self):
        with self.assertRaises(ValidationError):
            self.review_service.add_review(1, 1, 5, " ")