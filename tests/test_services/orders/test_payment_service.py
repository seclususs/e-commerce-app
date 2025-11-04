from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock, ANY

from app.services.orders.payment_service import PaymentService


class TestPaymentService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_order_repo = MagicMock()
        self.mock_item_repo = MagicMock()
        self.mock_history_repo = MagicMock()
        self.mock_product_repo = MagicMock()
        self.mock_variant_repo = MagicMock()
        self.mock_stock_svc = MagicMock()
        self.mock_variant_svc = MagicMock()
        
        self.payment_service = PaymentService(
            order_repo=self.mock_order_repo,
            item_repo=self.mock_item_repo,
            history_repo=self.mock_history_repo,
            product_repo=self.mock_product_repo,
            variant_repo=self.mock_variant_repo,
            stock_svc=self.mock_stock_svc,
            variant_svc=self.mock_variant_svc
        )
        
        self.transaction_id = "TRANS123"
        self.order_id = 1
        self.mock_order = {
            "id": self.order_id, "status": "Menunggu Pembayaran",
            "payment_method": "BANK_TRANSFER", "user_id": 1
        }
        self.mock_items = [
            {"order_id": 1, "product_id": 10, "variant_id": None, "quantity": 1},
            {"order_id": 1, "product_id": 11, "variant_id": 20, "quantity": 2}
        ]

    def tearDown(self):
        super().tearDown()

    def test_process_successful_payment_success(self):
        self.mock_order_repo.find_by_transaction_id.return_value = (
            self.mock_order
        )
        self.mock_item_repo.find_by_order_id.return_value = self.mock_items
        self.mock_stock_svc.get_available_stock.return_value = 10
        self.mock_product_repo.lock_stock.return_value = {"stock": 10}
        self.mock_variant_repo.lock_stock.return_value = {"stock": 10}
        self.mock_product_repo.decrease_stock.return_value = 1
        self.mock_variant_repo.decrease_stock.return_value = 1
        
        result = self.payment_service.process_successful_payment(
            self.transaction_id
        )
        
        self.mock_order_repo.find_by_transaction_id.assert_called_once()
        self.mock_item_repo.find_by_order_id.assert_called_once()
        self.assertEqual(self.mock_stock_svc.get_available_stock.call_count, 2)
        self.mock_product_repo.lock_stock.assert_called_once()
        self.mock_variant_repo.lock_stock.assert_called_once()
        self.mock_product_repo.decrease_stock.assert_called_once()
        self.mock_variant_repo.decrease_stock.assert_called_once()
        self.mock_order_repo.update_status.assert_called_once_with(
            self.db_conn, self.order_id, "Diproses"
        )
        self.mock_history_repo.create.assert_called_once()
        self.mock_stock_svc.release_stock_holds.assert_called_once()
        self.mock_variant_svc.update_total_stock_from_variants.assert_called_once()
        self.assertTrue(result["success"])

    def test_process_successful_payment_order_not_found(self):
        self.mock_order_repo.find_by_transaction_id.return_value = None
        
        result = self.payment_service.process_successful_payment(
            self.transaction_id
        )
        
        self.assertFalse(result["success"])
        self.assertIn("tidak ditemukan", result["message"])

    def test_process_successful_payment_already_processed(self):
        order_processed = self.mock_order.copy()
        order_processed["status"] = "Diproses"
        self.mock_order_repo.find_by_transaction_id.return_value = (
            order_processed
        )
        
        result = self.payment_service.process_successful_payment(
            self.transaction_id
        )
        
        self.assertTrue(result["success"])
        self.assertIn("sudah diproses", result["message"])

    def test_process_successful_payment_out_of_stock_check(self):
        self.mock_order_repo.find_by_transaction_id.return_value = (
            self.mock_order
        )
        self.mock_item_repo.find_by_order_id.return_value = self.mock_items
        self.mock_stock_svc.get_available_stock.side_effect = [10, 1]
        self.mock_product_repo.find_minimal_by_id.return_value = {"name": "Prod B"}
        self.mock_variant_repo.find_by_id.return_value = {"size": "L", "color": "Blue"}
        
        result = self.payment_service.process_successful_payment(
            self.transaction_id
        )
        
        self.mock_order_repo.update_status.assert_called_once_with(
            self.db_conn, self.order_id, "Dibatalkan"
        )
        self.mock_history_repo.create.assert_called_once_with(
            self.db_conn, self.order_id, "Dibatalkan", ANY
        )
        self.mock_stock_svc.release_stock_holds.assert_called_once()
        self.assertFalse(result["success"])
        self.assertIn("stok habis", result["message"])

    def test_process_successful_payment_out_of_stock_deduct(self):
        self.mock_order_repo.find_by_transaction_id.return_value = (
            self.mock_order
        )
        self.mock_item_repo.find_by_order_id.return_value = self.mock_items
        self.mock_stock_svc.get_available_stock.return_value = 10
        self.mock_product_repo.lock_stock.return_value = {"stock": 10}
        self.mock_variant_repo.lock_stock.return_value = {"stock": 1}
        
        result = self.payment_service.process_successful_payment(
            self.transaction_id
        )
        
        self.mock_order_repo.update_status.assert_called_once_with(
            ANY, self.order_id, "Dibatalkan"
        )
        self.mock_history_repo.create.assert_called_once_with(
            ANY, self.order_id, "Dibatalkan", ANY
        )
        self.assertFalse(result["success"])
        self.assertIn("stok habis", result["message"])