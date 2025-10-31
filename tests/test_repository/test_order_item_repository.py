from unittest.mock import MagicMock, patch

from tests.base_test_case import BaseTestCase
from app.repository.order_item_repository import (
    OrderItemRepository, order_item_repository
)


class TestOrderItemRepository(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_cursor = MagicMock()
        patch.object(
            self.db_conn, 'cursor', return_value=self.mock_cursor
        ).start()
        self.repository = OrderItemRepository()

    def test_singleton_instance(self):
        self.assertIsInstance(order_item_repository, OrderItemRepository)

    def test_find_by_order_id(self):
        mock_result = [{"id": 1, "product_id": 10}]
        self.mock_cursor.fetchall.return_value = mock_result
        
        result = self.repository.find_by_order_id(self.db_conn, 100)

        self.mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM order_items WHERE order_id = %s", (100,)
        )
        self.assertEqual(result, mock_result)
        self.mock_cursor.close.assert_called_once()

    def test_find_for_invoice(self):
        mock_result = [{"name": "Test", "quantity": 1}]
        self.mock_cursor.fetchall.return_value = mock_result
        
        result = self.repository.find_for_invoice(self.db_conn, 100)

        self.mock_cursor.execute.assert_called_once()
        self.assertIn("p.name, oi.quantity, oi.price",
                      self.mock_cursor.execute.call_args[0][0])
        self.assertEqual(result, mock_result)
        self.mock_cursor.close.assert_called_once()

    def test_find_for_admin_detail(self):
        mock_result = [{"name": "Test", "quantity": 1, "size_at_order": "M"}]
        self.mock_cursor.fetchall.return_value = mock_result
        
        result = self.repository.find_for_admin_detail(self.db_conn, 100)

        self.mock_cursor.execute.assert_called_once()
        self.assertIn("oi.size_at_order",
                      self.mock_cursor.execute.call_args[0][0])
        self.assertEqual(result, mock_result)
        self.mock_cursor.close.assert_called_once()

    def test_create_batch(self):
        items_data = [
            (100, 1, 1, 1, 10000, "M"),
            (100, 2, None, 2, 20000, None)
        ]
        self.mock_cursor.rowcount = 2
        
        result = self.repository.create_batch(self.db_conn, items_data)

        self.mock_cursor.executemany.assert_called_once_with(
            "\n                INSERT INTO order_items (\n"
            "                    order_id, product_id, variant_id, quantity, "
            "price,\n                    size_at_order\n"
            "                ) VALUES (%s, %s, %s, %s, %s, %s)\n"
            "                ",
            items_data
        )
        self.assertEqual(result, 2)
        self.mock_cursor.close.assert_called_once()