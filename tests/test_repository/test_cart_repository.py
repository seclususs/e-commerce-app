from unittest.mock import MagicMock, patch

from tests.base_test_case import BaseTestCase
from app.repository.cart_repository import (
    CartRepository, cart_repository
)


class TestCartRepository(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_cursor = MagicMock()
        self.cursor_patch = patch.object(
            self.db_conn, 'cursor', return_value=self.mock_cursor
        )
        self.cursor_patch.start()
        self.repository = CartRepository()

    def tearDown(self):
        self.cursor_patch.stop()
        super().tearDown()

    def test_singleton_instance(self):
        self.assertIsInstance(cart_repository, CartRepository)

    def test_get_user_cart_items(self):
        mock_result = [{"id": 1, "name": "Test"}]
        self.mock_cursor.fetchall.return_value = mock_result
        
        result = self.repository.get_user_cart_items(self.db_conn, 1)

        self.mock_cursor.execute.assert_called_once()
        self.assertEqual(result, mock_result)
        self.mock_cursor.close.assert_called_once()

    def test_find_cart_item_with_variant(self):
        mock_result = {"id": 10, "quantity": 1}
        self.mock_cursor.fetchone.return_value = mock_result
        
        result = self.repository.find_cart_item(self.db_conn, 1, 2, 3)

        expected_query = (
            "SELECT id, quantity FROM user_carts "
            "WHERE user_id = %s AND product_id = %s AND variant_id = %s"
        )
        self.mock_cursor.execute.assert_called_once_with(
            expected_query,
            (1, 2, 3)
        )
        self.assertEqual(result, mock_result)
        self.mock_cursor.close.assert_called_once()

    def test_find_cart_item_without_variant(self):
        self.mock_cursor.fetchone.return_value = None
        
        result = self.repository.find_cart_item(self.db_conn, 1, 2, None)

        expected_query = (
            "SELECT id, quantity FROM user_carts "
            "WHERE user_id = %s AND product_id = %s "
            "AND variant_id IS NULL"
        )
        self.mock_cursor.execute.assert_called_once_with(
            expected_query,
            (1, 2)
        )
        self.assertIsNone(result)
        self.mock_cursor.close.assert_called_once()

    def test_update_cart_quantity(self):
        self.mock_cursor.rowcount = 1
        
        result = self.repository.update_cart_quantity(self.db_conn, 10, 5)

        self.mock_cursor.execute.assert_called_once_with(
            "UPDATE user_carts SET quantity = %s WHERE id = %s",
            (5, 10)
        )
        self.assertEqual(result, 1)
        self.mock_cursor.close.assert_called_once()

    def test_create_cart_item(self):
        self.mock_cursor.lastrowid = 100
        
        result = self.repository.create_cart_item(self.db_conn, 1, 2, 3, 4)

        self.mock_cursor.execute.assert_called_once()
        self.assertEqual(result, 100)
        self.mock_cursor.close.assert_called_once()

    def test_delete_cart_item(self):
        self.mock_cursor.rowcount = 1
        
        result = self.repository.delete_cart_item(self.db_conn, 10)

        self.mock_cursor.execute.assert_called_once_with(
            "DELETE FROM user_carts WHERE id = %s", (10,)
        )
        self.assertEqual(result, 1)
        self.mock_cursor.close.assert_called_once()

    def test_clear_user_cart(self):
        self.mock_cursor.rowcount = 3
        
        result = self.repository.clear_user_cart(self.db_conn, 1)

        self.mock_cursor.execute.assert_called_once_with(
            "DELETE FROM user_carts WHERE user_id = %s", (1,)
        )
        self.assertEqual(result, 3)
        self.mock_cursor.close.assert_called_once()