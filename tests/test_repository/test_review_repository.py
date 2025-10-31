from unittest.mock import MagicMock, patch

from tests.base_test_case import BaseTestCase
from app.repository.review_repository import (
    ReviewRepository, review_repository
)


class TestReviewRepository(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_cursor = MagicMock()
        self.cursor_patch = patch.object(
            self.db_conn, 'cursor', return_value=self.mock_cursor
        )
        self.cursor_patch.start()
        self.repository = ReviewRepository()

    def tearDown(self):
        self.cursor_patch.stop()
        super().tearDown()

    def test_singleton_instance(self):
        self.assertIsInstance(review_repository, ReviewRepository)

    def test_find_by_product_id_with_user(self):
        mock_result = [{"id": 1, "username": "Test"}]
        self.mock_cursor.fetchall.return_value = mock_result
        
        result = self.repository.find_by_product_id_with_user(self.db_conn, 10)

        self.mock_cursor.execute.assert_called_once()
        query, params = self.mock_cursor.execute.call_args[0]
        self.assertIn("JOIN users u ON r.user_id = u.id", query)
        self.assertEqual(params, (10,))
        self.assertEqual(result, mock_result)
        self.mock_cursor.close.assert_called_once()

    def test_find_by_id_with_user(self):
        mock_result = {"id": 1, "username": "Test"}
        self.mock_cursor.fetchone.return_value = mock_result
        
        result = self.repository.find_by_id_with_user(self.db_conn, 1)

        self.mock_cursor.execute.assert_called_once()
        query, params = self.mock_cursor.execute.call_args[0]
        self.assertIn("r.id = %s", query)
        self.assertEqual(params, (1,))
        self.assertEqual(result, mock_result)
        self.mock_cursor.close.assert_called_once()

    def test_check_user_purchase_true(self):
        self.mock_cursor.fetchone.return_value = {"1": 1}
        
        result = self.repository.check_user_purchase(self.db_conn, 1, 10)

        self.mock_cursor.execute.assert_called_once()
        query, params = self.mock_cursor.execute.call_args[0]
        self.assertIn("o.status = 'Selesai'", query)
        self.assertEqual(params, (1, 10))
        self.assertTrue(result)
        self.mock_cursor.close.assert_called_once()

    def test_check_user_purchase_false(self):
        self.mock_cursor.fetchone.return_value = None
        
        result = self.repository.check_user_purchase(self.db_conn, 1, 10)

        self.assertFalse(result)
        self.mock_cursor.close.assert_called_once()

    def test_check_user_review_exists_true(self):
        self.mock_cursor.fetchone.return_value = {"1": 1}
        
        result = self.repository.check_user_review_exists(self.db_conn, 1, 10)

        self.mock_cursor.execute.assert_called_once_with(
            "SELECT 1 FROM reviews "
            "WHERE user_id = %s AND product_id = %s LIMIT 1",
            (1, 10)
        )
        self.assertTrue(result)
        self.mock_cursor.close.assert_called_once()

    def test_check_user_review_exists_false(self):
        self.mock_cursor.fetchone.return_value = None
        
        result = self.repository.check_user_review_exists(self.db_conn, 1, 10)

        self.assertFalse(result)
        self.mock_cursor.close.assert_called_once()

    def test_create(self):
        self.mock_cursor.lastrowid = 5
        
        result = self.repository.create(
            self.db_conn, 1, 10, 5, " Comment "
        )

        self.mock_cursor.execute.assert_called_once()
        query, params = self.mock_cursor.execute.call_args[0]
        self.assertIn(
            "INSERT INTO reviews (product_id, user_id, rating, comment)",
            query
        )
        self.assertEqual(params, (10, 1, 5, "Comment"))
        self.assertEqual(result, 5)
        self.mock_cursor.close.assert_called_once()