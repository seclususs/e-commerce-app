from unittest.mock import MagicMock, patch

from tests.base_test_case import BaseTestCase
from app.repository.order_status_history_repository import (
    OrderStatusHistoryRepository, order_status_history_repository
)


class TestOrderStatusHistoryRepository(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_cursor = MagicMock()
        self.cursor_patch = patch.object(
            self.db_conn, 'cursor', return_value=self.mock_cursor
        )
        self.cursor_patch.start()
        self.repository = OrderStatusHistoryRepository()

    def tearDown(self):
        self.cursor_patch.stop()
        super().tearDown()

    def test_singleton_instance(self):
        self.assertIsInstance(
            order_status_history_repository, OrderStatusHistoryRepository
        )

    def test_create_with_notes(self):
        self.mock_cursor.lastrowid = 1
        
        result = self.repository.create(
            self.db_conn, 100, "Diproses", "Order diterima"
        )

        self.mock_cursor.execute.assert_called_once()
        self.assertIn("VALUES (%s, %s, %s)",
                      self.mock_cursor.execute.call_args[0][0])
        params = self.mock_cursor.execute.call_args[0][1]
        self.assertEqual(
            params,
            (100, "Diproses", "Order diterima")
        )
        self.assertEqual(result, 1)
        self.mock_cursor.close.assert_called_once()

    def test_create_without_notes(self):
        self.mock_cursor.lastrowid = 2
        
        result = self.repository.create(self.db_conn, 101, "Selesai")

        self.mock_cursor.execute.assert_called_once()
        params = self.mock_cursor.execute.call_args[0][1]
        self.assertEqual(
            params,
            (101, "Selesai", None)
        )
        self.assertEqual(result, 2)
        self.mock_cursor.close.assert_called_once()