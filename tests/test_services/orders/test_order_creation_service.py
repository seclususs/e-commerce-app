from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock, patch
from decimal import Decimal

from app.services.orders.order_creation_service import OrderCreationService
from app.exceptions.api_exceptions import ValidationError


class TestOrderCreationService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_stock_repo = MagicMock()
        self.mock_product_repo = MagicMock()
        self.mock_order_repo = MagicMock()
        self.mock_order_item_repo = MagicMock()
        self.mock_history_repo = MagicMock()
        self.mock_voucher_repo = MagicMock()
        self.mock_cart_repo = MagicMock()
        self.mock_discount_svc = MagicMock()
        self.mock_stock_svc = MagicMock()
        self.mock_variant_svc = MagicMock()
        
        self.patch_uuid = patch(
            'app.services.orders.order_creation_service.uuid.uuid4'
        )
        
        self.mock_uuid = self.patch_uuid.start()
        self.mock_uuid.return_value.hex = '1234567890abcdef'
        
        self.order_creation_service = OrderCreationService(
            stock_repo=self.mock_stock_repo,
            product_repo=self.mock_product_repo,
            order_repo=self.mock_order_repo,
            order_item_repo=self.mock_order_item_repo,
            history_repo=self.mock_history_repo,
            voucher_repo=self.mock_voucher_repo,
            cart_repo=self.mock_cart_repo,
            discount_svc=self.mock_discount_svc,
            stock_svc=self.mock_stock_svc,
            variant_svc=self.mock_variant_svc
        )
        
        self.shipping_details = {
            "name": "Test User", "phone": "123", "address1": "Street",
            "city": "City", "province": "Prov", "postal_code": "123",
            "email": "a@b.c"
        }
        self.held_items = [
            {"product_id": 1, "name": "Prod A", "quantity": 1,
             "variant_id": None, "size": None}
        ]
        self.products_db = [
            {"id": 1, "name": "Prod A", "price": 100, "discount_price": None}
        ]
        self.items_for_order = [
            {"id": 1, "name": "Prod A", "price": 100, "discount_price": None,
             "quantity": 1, "price_at_order": 100, "variant_id": None,
             "size": None}
        ]

    def tearDown(self):
        self.patch_uuid.stop()
        super().tearDown()

    def test_create_order_success_user_bank(self):
        self.mock_stock_repo.find_detailed_by_user_id.return_value = (
            self.held_items
        )
        self.mock_product_repo.find_batch_for_order.return_value = (
            self.products_db
        )
        self.mock_discount_svc.validate_and_calculate_voucher.return_value = (
            {"success": False}
        )
        self.mock_order_repo.create.return_value = 1
        
        result = self.order_creation_service.create_order(
            user_id=1, session_id=None,
            shipping_details=self.shipping_details,
            payment_method="BANK_TRANSFER", shipping_cost=10.0
        )
        
        self.mock_stock_repo.find_detailed_by_user_id.assert_called_once()
        self.mock_product_repo.find_batch_for_order.assert_called_once()
        self.mock_order_repo.create.assert_called_once_with(
            self.db_conn, 1, Decimal("100"), Decimal("0"), Decimal("10.0"),
            Decimal("110.0"), None, "BANK_TRANSFER", "TX-12345678",
            self.shipping_details
        )
        self.mock_order_item_repo.create_batch.assert_called_once()
        self.mock_history_repo.create.assert_called()
        self.mock_order_repo.update_status.assert_called_once_with(
            self.db_conn, 1, "Menunggu Pembayaran"
        )
        self.mock_cart_repo.clear_user_cart.assert_called_once()
        self.mock_stock_svc.release_stock_holds.assert_called_once()
        self.assertEqual(result, {"success": True, "order_id": 1})

    def test_create_order_success_guest_cod_with_voucher(self):
        self.mock_stock_repo.find_detailed_by_session_id.return_value = (
            self.held_items
        )
        self.mock_product_repo.find_batch_for_order.return_value = (
            self.products_db
        )
        self.mock_discount_svc.validate_and_calculate_voucher.return_value = (
            {"success": True, "discount_amount": 10.0}
        )
        self.mock_order_repo.create.return_value = 2
        self.mock_product_repo.lock_stock.return_value = {"stock": 10}
        self.mock_product_repo.decrease_stock.return_value = 1
        self.mock_variant_svc.variant_repository = MagicMock()
        self.mock_variant_svc.variant_repository.lock_stock.return_value = {"stock": 10}
        self.mock_variant_svc.variant_repository.decrease_stock.return_value = 1
        
        result = self.order_creation_service.create_order(
            user_id=None, session_id="sess_id",
            shipping_details=self.shipping_details, payment_method="COD",
            voucher_code="DISKON10", shipping_cost=5.0
        )
        
        self.mock_stock_repo.find_detailed_by_session_id.assert_called_once()
        self.mock_discount_svc.validate_and_calculate_voucher.assert_called_once()
        self.mock_order_repo.create.assert_called_once_with(
            self.db_conn, None, Decimal("100"), Decimal("10.0"),
            Decimal("5.0"), Decimal("95.0"), "DISKON10", "COD", None,
            self.shipping_details
        )
        self.mock_order_repo.update_status.assert_called_once_with(
            self.db_conn, 2, "Diproses"
        )
        self.mock_voucher_repo.increment_use_count.assert_called_once()
        self.mock_cart_repo.clear_user_cart.assert_not_called()
        self.assertEqual(result, {"success": True, "order_id": 2})

    def test_create_order_no_held_items(self):
        self.mock_stock_repo.find_detailed_by_user_id.return_value = []
        
        result = self.order_creation_service.create_order(
            user_id=1, session_id=None,
            shipping_details=self.shipping_details,
            payment_method="BANK_TRANSFER"
        )
        
        self.assertEqual(result["success"], False)
        self.assertIn("Sesi checkout", result["message"])
        self.mock_order_repo.create.assert_not_called()

    def test_create_order_product_not_found_during_prepare(self):
        self.mock_stock_repo.find_detailed_by_user_id.return_value = (
            self.held_items
        )
        self.mock_product_repo.find_batch_for_order.return_value = []
        
        result = self.order_creation_service.create_order(
            user_id=1, session_id=None,
            shipping_details=self.shipping_details,
            payment_method="BANK_TRANSFER"
        )
        
        self.assertEqual(result["success"], False)
        self.assertIn("tidak lagi tersedia", result["message"])
        self.mock_order_repo.create.assert_not_called()

    def test_create_order_voucher_invalid(self):
        self.mock_stock_repo.find_detailed_by_user_id.return_value = (
            self.held_items
        )
        self.mock_product_repo.find_batch_for_order.return_value = (
            self.products_db
        )
        self.mock_discount_svc.validate_and_calculate_voucher.return_value = (
            {"success": False, "message": "Voucher expired"}
        )
        
        result = self.order_creation_service.create_order(
            user_id=1, session_id=None,
            shipping_details=self.shipping_details,
            payment_method="BANK_TRANSFER", voucher_code="INVALID"
        )
        
        self.assertEqual(result["success"], False)
        self.assertEqual(result["message"], "Voucher expired")
        self.mock_order_repo.create.assert_not_called()