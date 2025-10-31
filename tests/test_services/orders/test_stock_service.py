from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock, patch
from datetime import datetime

from app.services.orders.stock_service import StockService

class TestStockService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_stock_repo = MagicMock()
        self.mock_product_repo = MagicMock()
        self.mock_variant_repo = MagicMock()
        self.mock_order_item_repo = MagicMock()
        self.mock_variant_svc = MagicMock()
        
        self.patch_datetime = patch(
            'app.services.orders.stock_service.datetime'
        )
        
        self.mock_datetime = self.patch_datetime.start()
        self.mock_datetime.now.return_value = datetime(2025, 1, 1, 12, 0, 0)
        
        self.stock_service = StockService(
            stock_repo=self.mock_stock_repo,
            product_repo=self.mock_product_repo,
            variant_repo=self.mock_variant_repo,
            order_item_repo=self.mock_order_item_repo,
            variant_svc=self.mock_variant_svc
        )
        
        self.cart_items = [
            {"product_id": 1, "variant_id": None, "quantity": 1, "name": "A"},
            {"product_id": 2, "variant_id": 10, "quantity": 2, "name": "B",
             "size": "M"}
        ]

    def tearDown(self):
        self.patch_datetime.stop()
        super().tearDown()

    def test_get_available_stock_no_variant(self):
        self.mock_stock_repo.delete_expired.return_value = 0
        self.mock_product_repo.get_stock.return_value = {"stock": 10}
        self.mock_stock_repo.get_held_stock_sum.return_value = 2
        
        stock = self.stock_service.get_available_stock(product_id=1)
        
        self.mock_stock_repo.delete_expired.assert_called_once()
        self.mock_product_repo.get_stock.assert_called_once_with(
            self.db_conn, 1
        )
        self.mock_stock_repo.get_held_stock_sum.assert_called_once_with(
            self.db_conn, 1, None
        )
        self.assertEqual(stock, 8)

    def test_get_available_stock_with_variant(self):
        self.mock_stock_repo.delete_expired.return_value = 1
        self.mock_variant_repo.get_stock.return_value = {"stock": 5}
        self.mock_stock_repo.get_held_stock_sum.return_value = 1
        
        stock = self.stock_service.get_available_stock(
            product_id=1, variant_id=10
        )
        
        self.mock_variant_repo.get_stock.assert_called_once_with(
            self.db_conn, 10
        )
        self.mock_stock_repo.get_held_stock_sum.assert_called_once_with(
            self.db_conn, 1, 10
        )
        self.assertEqual(stock, 4)

    def test_hold_stock_for_checkout_success(self):
        self.mock_stock_repo.delete_by_user_id.return_value = 0
        self.stock_service.get_available_stock = MagicMock(return_value=10)
        self.mock_stock_repo.create_batch.return_value = 2
        
        result = self.stock_service.hold_stock_for_checkout(
            user_id=1, session_id=None, cart_items=self.cart_items
        )
        
        self.mock_stock_repo.delete_by_user_id.assert_called_once_with(
            self.db_conn, 1
        )
        self.assertEqual(self.stock_service.get_available_stock.call_count, 2)
        self.mock_stock_repo.create_batch.assert_called_once()
        self.assertTrue(result["success"])
        self.assertIn("expires_at", result)

    def test_hold_stock_for_checkout_out_of_stock(self):
        self.mock_stock_repo.delete_by_user_id.return_value = 0
        self.stock_service.get_available_stock = MagicMock(
            side_effect=[10, 1]
        )
        
        result = self.stock_service.hold_stock_for_checkout(
            user_id=1, session_id=None, cart_items=self.cart_items
        )
        
        self.assertEqual(self.stock_service.get_available_stock.call_count, 2)
        self.mock_stock_repo.create_batch.assert_not_called()
        self.assertFalse(result["success"])
        self.assertIn("tidak mencukupi", result["message"])

    def test_release_stock_holds_user(self):
        self.stock_service.release_stock_holds(1, None, self.db_conn)
        self.mock_stock_repo.delete_by_user_id.assert_called_once_with(
            self.db_conn, 1
        )
        self.mock_stock_repo.delete_by_session_id.assert_not_called()

    def test_get_held_items_simple_user(self):
        mock_held = [{"product_id": 1, "quantity": 1}]
        self.mock_stock_repo.find_simple_by_user_id.return_value = mock_held
        
        result = self.stock_service.get_held_items_simple(1, None)
        
        self.assertEqual(result, mock_held)

    def test_restock_items_for_order_success(self):
        mock_items = [
            {"product_id": 1, "variant_id": None, "quantity": 1},
            {"product_id": 2, "variant_id": 10, "quantity": 2}
        ]
        self.mock_order_item_repo.find_by_order_id.return_value = mock_items
        self.mock_product_repo.increase_stock.return_value = 1
        self.mock_variant_repo.increase_stock.return_value = 1
        
        self.stock_service.restock_items_for_order(1, self.db_conn)
        
        self.mock_order_item_repo.find_by_order_id.assert_called_once_with(
            self.db_conn, 1
        )
        self.mock_product_repo.increase_stock.assert_called_once_with(
            self.db_conn, 1, 1
        )
        self.mock_variant_repo.increase_stock.assert_called_once_with(
            self.db_conn, 10, 2
        )
        self.mock_variant_svc.update_total_stock_from_variants.assert_called_once_with(
            2, self.db_conn
        )