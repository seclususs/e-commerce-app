from unittest.mock import MagicMock, patch

from tests.base_test_case import BaseTestCase
from app.repository.stock_repository import (
    StockRepository, stock_repository
)


class TestStockRepository(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_cursor = MagicMock()
        patch.object(
            self.db_conn, 'cursor', return_value=self.mock_cursor
        ).start()
        self.repository = StockRepository()

    def test_singleton_instance(self):
        self.assertIsInstance(stock_repository, StockRepository)

    def test_delete_expired(self):
        self.mock_cursor.rowcount = 2
        
        result = self.repository.delete_expired(self.db_conn)

        self.mock_cursor.execute.assert_called_once_with(
            "DELETE FROM stock_holds WHERE expires_at < CURRENT_TIMESTAMP"
        )
        self.assertEqual(result, 2)
        self.mock_cursor.close.assert_called_once()

    def test_get_held_stock_sum_with_variant(self):
        self.mock_cursor.fetchone.return_value = {"held": 5}
        
        result = self.repository.get_held_stock_sum(self.db_conn, 1, 10)

        self.mock_cursor.execute.assert_called_once_with(
            "SELECT SUM(quantity) as held FROM stock_holds "
            "WHERE product_id = %s AND variant_id = %s",
            (1, 10)
        )
        self.assertEqual(result, 5)
        self.mock_cursor.close.assert_called_once()

    def test_get_held_stock_sum_no_variant(self):
        self.mock_cursor.fetchone.return_value = {"held": 3}
        
        result = self.repository.get_held_stock_sum(self.db_conn, 1, None)

        self.mock_cursor.execute.assert_called_once_with(
            "SELECT SUM(quantity) as held FROM stock_holds "
            "WHERE product_id = %s AND variant_id IS NULL",
            (1,)
        )
        self.assertEqual(result, 3)
        self.mock_cursor.close.assert_called_once()

    def test_get_held_stock_sum_no_holds(self):
        self.mock_cursor.fetchone.return_value = {"held": None}
        
        result = self.repository.get_held_stock_sum(self.db_conn, 1, None)

        self.assertEqual(result, 0)
        self.mock_cursor.close.assert_called_once()

    def test_delete_by_user_id(self):
        self.mock_cursor.rowcount = 2
        
        result = self.repository.delete_by_user_id(self.db_conn, 1)

        self.mock_cursor.execute.assert_called_once_with(
            "DELETE FROM stock_holds WHERE user_id = %s", (1,)
        )
        self.assertEqual(result, 2)
        self.mock_cursor.close.assert_called_once()

    def test_delete_by_session_id(self):
        self.mock_cursor.rowcount = 1
        
        result = self.repository.delete_by_session_id(self.db_conn, "sess123")

        self.mock_cursor.execute.assert_called_once_with(
            "DELETE FROM stock_holds WHERE session_id = %s", ("sess123",)
        )
        self.assertEqual(result, 1)
        self.mock_cursor.close.assert_called_once()

    def test_create_batch(self):
        holds_data = [
            (1, None, 1, 10, 1, "2025-01-01 12:00:00"),
            (None, "sess123", 2, None, 2, "2025-01-01 12:00:00")
        ]
        self.mock_cursor.rowcount = 2
        
        result = self.repository.create_batch(self.db_conn, holds_data)

        self.mock_cursor.executemany.assert_called_once()
        self.assertEqual(result, 2)
        self.mock_cursor.close.assert_called_once()

    def test_find_simple_by_user_id(self):
        self.repository.find_simple_by_user_id(self.db_conn, 1)
        
        self.mock_cursor.execute.assert_called_once()
        query = self.mock_cursor.execute.call_args[0][0]
        self.assertIn("user_id = %s", query)
        self.mock_cursor.close.assert_called_once()

    def test_find_simple_by_session_id(self):
        self.repository.find_simple_by_session_id(self.db_conn, "sess123")
        
        self.mock_cursor.execute.assert_called_once()
        query = self.mock_cursor.execute.call_args[0][0]
        self.assertIn("session_id = %s", query)
        self.mock_cursor.close.assert_called_once()

    def test_find_detailed_by_user_id(self):
        self.repository.find_detailed_by_user_id(self.db_conn, 1)
        
        self.mock_cursor.execute.assert_called_once()
        query = self.mock_cursor.execute.call_args[0][0]
        self.assertIn("JOIN products p", query)
        self.assertIn("LEFT JOIN product_variants pv", query)
        self.assertIn("sh.user_id = %s", query)
        self.mock_cursor.close.assert_called_once()

    def test_find_detailed_by_session_id(self):
        self.repository.find_detailed_by_session_id(self.db_conn, "sess123")
        
        self.mock_cursor.execute.assert_called_once()
        query = self.mock_cursor.execute.call_args[0][0]
        self.assertIn("sh.session_id = %s", query)
        self.mock_cursor.close.assert_called_once()