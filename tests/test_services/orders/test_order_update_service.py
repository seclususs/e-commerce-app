from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock, patch

from app.services.orders.order_update_service import OrderUpdateService
from app.exceptions.database_exceptions import RecordNotFoundError


@patch('app.services.orders.order_update_service.status_class_filter', return_value='status-class')
class TestOrderUpdateService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_order_repo = MagicMock()
        self.mock_history_repo = MagicMock()
        self.mock_cancel_svc = MagicMock()
        
        self.order_update_service = OrderUpdateService(
            order_repo=self.mock_order_repo,
            history_repo=self.mock_history_repo,
            cancel_svc=self.mock_cancel_svc
        )
        
        self.order_id = 1

    def tearDown(self):
        super().tearDown()

    def test_update_status_success_status_change(self, mock_status_filter):
        mock_order = {"status": "Diproses", "tracking_number": None}
        self.mock_order_repo.find_by_id_for_update.return_value = mock_order
        
        result = (
            self.order_update_service.update_order_status_and_tracking(
                self.order_id, "Dikirim", "TRACK123"
            )
        )
        
        self.mock_order_repo.update_status_and_tracking.assert_called_once_with(
            self.db_conn, 1, "Dikirim", "TRACK123"
        )
        self.mock_history_repo.create.assert_called_once()
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["status"], "Dikirim")
        self.assertEqual(result["data"]["tracking_number"], "TRACK123")

    def test_update_status_success_tracking_change(self, mock_status_filter):
        mock_order = {"status": "Dikirim", "tracking_number": "OLDTRACK"}
        self.mock_order_repo.find_by_id_for_update.return_value = mock_order
        
        result = (
            self.order_update_service.update_order_status_and_tracking(
                self.order_id, "Dikirim", "NEWTRACK"
            )
        )
        
        self.mock_order_repo.update_status_and_tracking.assert_called_once_with(
            self.db_conn, 1, "Dikirim", "NEWTRACK"
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["tracking_number"], "NEWTRACK")

    def test_update_status_no_change(self, mock_status_filter):
        mock_order = {"status": "Dikirim", "tracking_number": "TRACK123"}
        self.mock_order_repo.find_by_id_for_update.return_value = mock_order
        
        result = (
            self.order_update_service.update_order_status_and_tracking(
                self.order_id, "Dikirim", "TRACK123"
            )
        )
        
        self.mock_order_repo.update_status_and_tracking.assert_not_called()
        self.assertTrue(result["success"])
        self.assertIn("Tidak ada perubahan", result["message"])

    def test_update_status_to_cancelled(self, mock_status_filter):
        self.mock_cancel_svc.cancel_admin_order.return_value = {
            "success": True,
            "message": "Cancelled",
            "data": {"status": "Dibatalkan"}
        }
        
        result = (
            self.order_update_service.update_order_status_and_tracking(
                self.order_id, "Dibatalkan", None
            )
        )
        
        self.mock_cancel_svc.cancel_admin_order.assert_called_once_with(
            self.order_id
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["status"], "Dibatalkan")

    def test_update_status_order_not_found(self, mock_status_filter):
        self.mock_order_repo.find_by_id_for_update.return_value = None
        
        with self.assertRaises(RecordNotFoundError):
            (
                self.order_update_service.update_order_status_and_tracking(
                    self.order_id, "Dikirim", None
                )
            )