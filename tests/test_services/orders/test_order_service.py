from tests.base_test_case import BaseTestCase
from unittest.mock import patch

from app.services.orders.order_service import OrderService
from app.exceptions.service_exceptions import ServiceLogicError


@patch('app.services.orders.order_service.order_creation_service')
@patch('app.services.orders.order_service.order_cancel_service')
@patch('app.services.orders.order_service.order_update_service')
class TestOrderService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.order_service = OrderService()
        self.user_id = 1
        self.session_id = "sess_id"
        self.order_id = 100
        self.shipping_details = {"name": "Test"}
        self.cart_data = {"1-1": {"quantity": 1}}

    def tearDown(self):
        super().tearDown()

    def test_create_order(
        self, mock_update, mock_cancel, mock_creation
    ):
        mock_creation.create_order.return_value = {"success": True}
        
        result = self.order_service.create_order(
            self.user_id, self.session_id, self.cart_data, self.shipping_details, "COD",
            voucher_code="TEST", shipping_cost=10.0
        )
        
        mock_creation.create_order.assert_called_once_with(
            self.user_id, self.session_id, self.cart_data, self.shipping_details, "COD", "TEST", 10.0
        )
        self.assertEqual(result, {"success": True})

    def test_create_order_error(
        self, mock_update, mock_cancel, mock_creation
    ):
        mock_creation.create_order.side_effect = Exception("Create Error")
        
        with self.assertRaises(ServiceLogicError):
            self.order_service.create_order(
                self.user_id, self.session_id, self.cart_data, self.shipping_details, "COD"
            )

    def test_cancel_user_order(
        self, mock_update, mock_cancel, mock_creation
    ):
        mock_cancel.cancel_user_order.return_value = {"success": True}
        
        result = self.order_service.cancel_user_order(
            self.order_id, self.user_id
        )
        
        mock_cancel.cancel_user_order.assert_called_once_with(
            self.order_id, self.user_id
        )
        self.assertEqual(result, {"success": True})

    def test_cancel_user_order_error(
        self, mock_update, mock_cancel, mock_creation
    ):
        mock_cancel.cancel_user_order.side_effect = Exception("Cancel Error")
        
        with self.assertRaises(ServiceLogicError):
            self.order_service.cancel_user_order(
                self.order_id, self.user_id
            )

    def test_update_order_status_and_tracking(
        self, mock_update, mock_cancel, mock_creation
    ):
        mock_update.update_order_status_and_tracking.return_value = {
            "success": True
        }
        
        result = self.order_service.update_order_status_and_tracking(
            self.order_id, "Dikirim", "TRACK123"
        )
        
        mock_update.update_order_status_and_tracking.assert_called_once_with(
            self.order_id, "Dikirim", "TRACK123"
        )
        self.assertEqual(result, {"success": True})

    def test_update_order_status_and_tracking_error(
        self, mock_update, mock_cancel, mock_creation
    ):
        mock_update.update_order_status_and_tracking.side_effect = (
            Exception("Update Error")
        )
        
        with self.assertRaises(ServiceLogicError):
            self.order_service.update_order_status_and_tracking(
                self.order_id, "Dikirim", "TRACK123"
            )