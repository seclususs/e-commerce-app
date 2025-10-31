from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock

from app.services.orders.cart_service import CartService


class TestCartService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_cart_repo = MagicMock()
        self.mock_product_repo = MagicMock()
        self.mock_variant_repo = MagicMock()
        self.mock_stock_svc = MagicMock()
        
        self.cart_service = CartService(
            cart_repo=self.mock_cart_repo,
            product_repo=self.mock_product_repo,
            variant_repo=self.mock_variant_repo,
            stock_svc=self.mock_stock_svc
        )

    def tearDown(self):
        super().tearDown()

    def test_get_cart_details_success(self):
        mock_items = [{
            "id": 1, "name": "Test", "price": 100, "discount_price": None,
            "quantity": 2, "variant_id": None
        }]
        self.mock_cart_repo.get_user_cart_items.return_value = mock_items
        self.mock_stock_svc.get_available_stock.return_value = 10
        
        result = self.cart_service.get_cart_details(1)
        
        self.mock_stock_svc.get_available_stock.assert_called_once_with(
            1, None, self.db_conn
        )
        self.assertEqual(result["subtotal"], 200.0)
        self.assertEqual(result["items"][0]["stock"], 10)

    def test_add_to_cart_success_new_item(self):
        mock_product = {"id": 1, "name": "Test", "has_variants": False}
        self.mock_product_repo.find_minimal_by_id.return_value = mock_product
        self.mock_stock_svc.get_available_stock.return_value = 10
        self.mock_cart_repo.find_cart_item.return_value = None
        
        result = self.cart_service.add_to_cart(1, 1, 2)
        
        self.mock_cart_repo.create_cart_item.assert_called_once_with(
            self.db_conn, 1, 1, None, 2
        )
        self.assertEqual(result["success"], True)

    def test_add_to_cart_success_update_quantity(self):
        mock_product = {"id": 1, "name": "Test", "has_variants": False}
        self.mock_product_repo.find_minimal_by_id.return_value = mock_product
        self.mock_stock_svc.get_available_stock.return_value = 10
        existing_item = {"id": 100, "quantity": 1}
        self.mock_cart_repo.find_cart_item.return_value = existing_item
        
        result = self.cart_service.add_to_cart(1, 1, 2)
        
        self.mock_cart_repo.update_cart_quantity.assert_called_once_with(
            self.db_conn, 100, 3
        )
        self.assertEqual(result["success"], True)

    def test_add_to_cart_out_of_stock(self):
        mock_product = {"id": 1, "name": "Test", "has_variants": False}
        self.mock_product_repo.find_minimal_by_id.return_value = mock_product
        self.mock_stock_svc.get_available_stock.return_value = 5
        self.mock_cart_repo.find_cart_item.return_value = None
        
        result = self.cart_service.add_to_cart(1, 1, 10)
        
        self.assertEqual(result["success"], False)
        self.assertIn("Stok", result["message"])

    def test_add_to_cart_variant_required(self):
        mock_product = {"id": 1, "name": "Test", "has_variants": True}
        self.mock_product_repo.find_minimal_by_id.return_value = mock_product
        
        result = self.cart_service.add_to_cart(1, 1, 1)
        
        self.assertEqual(result["success"], False)
        self.assertIn("ukuran", result["message"])

    def test_update_cart_item_success(self):
        existing_item = {"id": 100, "quantity": 1}
        self.mock_cart_repo.find_cart_item.return_value = existing_item
        self.mock_stock_svc.get_available_stock.return_value = 10
        
        result = self.cart_service.update_cart_item(1, 1, 5)
        
        self.mock_cart_repo.update_cart_quantity.assert_called_once_with(
            self.db_conn, 100, 5
        )
        self.assertEqual(result["success"], True)

    def test_update_cart_item_delete(self):
        existing_item = {"id": 100, "quantity": 1}
        self.mock_cart_repo.find_cart_item.return_value = existing_item
        
        result = self.cart_service.update_cart_item(1, 1, 0)
        
        self.mock_cart_repo.delete_cart_item.assert_called_once_with(
            self.db_conn, 100
        )
        self.mock_cart_repo.update_cart_quantity.assert_not_called()
        self.assertEqual(result["success"], True)