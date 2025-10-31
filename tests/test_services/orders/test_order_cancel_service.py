from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock

from app.services.orders.order_cancel_service import OrderCancelService
from app.exceptions.service_exceptions import InvalidOperationError


class TestOrderCancelService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_order_repo = MagicMock()
        self.mock_history_repo = MagicMock()
        self.mock_stock_svc = MagicMock()
        
        self.order_cancel_service = OrderCancelService(
            order_repo=self.mock_order_repo,
            history_repo=self.mock_history_repo,
            stock_svc=self.mock_stock_svc
        )

    def tearDown(self):
        super().tearDown()

    def test_cancel_user_order_success_pending(self):
        mock_order = {"id": 1, "status": "Menunggu Pembayaran"}
        (
            self.mock_order_repo.
            find_by_id_and_user_id_for_update.return_value
        ) = mock_order
        
        result = self.order_cancel_service.cancel_user_order(1, 1)
        
        self.mock_order_repo.update_status.assert_called_once_with(
            self.db_conn, 1, "Dibatalkan"
        )
        self.mock_history_repo.create.assert_called_once()
        self.mock_stock_svc.restock_items_for_order.assert_not_called()
        self.assertTrue(result["success"])

    def test_cancel_user_order_success_processed(self):
        mock_order = {"id": 1, "status": "Diproses"}
        (
            self.mock_order_repo.
            find_by_id_and_user_id_for_update.return_value
        ) = mock_order
        
        result = self.order_cancel_service.cancel_user_order(1, 1)
        
        self.mock_stock_svc.restock_items_for_order.assert_called_once_with(
            1, self.db_conn
        )
        self.mock_order_repo.update_status.assert_called_once_with(
            self.db_conn, 1, "Dibatalkan"
        )
        self.assertTrue(result["success"])

    def test_cancel_user_order_not_found(self):
        (
            self.mock_order_repo.
            find_by_id_and_user_id_for_update.return_value
        ) = None
        
        result = self.order_cancel_service.cancel_user_order(1, 1)
        
        self.assertFalse(result["success"])
        self.assertIn("tidak ditemukan", result["message"])

    def test_cancel_user_order_invalid_status(self):
        mock_order = {"id": 1, "status": "Dikirim"}
        (
            self.mock_order_repo.
            find_by_id_and_user_id_for_update.return_value
        ) = mock_order
        
        result = self.order_cancel_service.cancel_user_order(1, 1)
        
        self.assertFalse(result["success"])
        self.assertIn("tidak dapat dibatalkan", result["message"])

    def test_cancel_admin_order_success(self):
        mock_order = {"id": 1, "status": "Diproses"}
        self.mock_order_repo.find_by_id_for_update.return_value = mock_order
        
        result = self.order_cancel_service.cancel_admin_order(1)
        
        self.mock_stock_svc.restock_items_for_order.assert_called_once_with(
            1, self.db_conn
        )
        self.mock_order_repo.update_status.assert_called_once_with(
            self.db_conn, 1, "Dibatalkan"
        )
        self.assertTrue(result["success"])

    def test_cancel_admin_order_already_cancelled(self):
        mock_order = {"id": 1, "status": "Dibatalkan"}
        self.mock_order_repo.find_by_id_for_update.return_value = mock_order
        
        with self.assertRaises(InvalidOperationError):
            self.order_cancel_service.cancel_admin_order(1)