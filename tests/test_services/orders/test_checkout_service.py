from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock, patch

from app.services.orders.checkout_service import CheckoutService


def mock_url_for(endpoint, **values):
    if endpoint == 'auth.login':
        return f'/login/?next={values.get("next", "")}'
    if endpoint == 'purchase.checkout':
        return '/checkout/'
    if endpoint == 'purchase.edit_address':
        return '/edit_address/'
    if endpoint == 'purchase.cart_page':
        return '/cart_page/'
    if endpoint == 'purchase.payment_page':
        order_id = values.get('order_id')
        return f'/payment_page/{order_id}/' if order_id else '/payment_page/'
    if endpoint == 'purchase.order_success':
        return '/order_success/'
    return f'/{endpoint}/mock-url/'


class TestCheckoutService(BaseTestCase):

    def setUp(self):
        super().setUp()
        
        self.patch_checkout_validation = patch('app.services.orders.checkout_service.checkout_validation_service')
        self.patch_order_creation = patch('app.services.orders.checkout_service.order_creation_service')
        self.patch_stock_service = patch('app.services.orders.checkout_service.stock_service')
        self.patch_user_service = patch('app.services.orders.checkout_service.user_service')

        self.mock_validation_svc = self.patch_checkout_validation.start()
        self.mock_creation_svc = self.patch_order_creation.start()
        self.mock_stock_svc = self.patch_stock_service.start()
        self.mock_user_svc = self.patch_user_service.start()
        
        self.patch_session = patch(
            'app.services.orders.checkout_service.session',
            MagicMock()
        )
        self.patch_url_for = patch(
            'app.services.orders.checkout_service.url_for',
            side_effect=mock_url_for
        )
        self.patch_json = patch(
            'app.services.orders.checkout_service.json'
        )
        
        self.mock_session = self.patch_session.start()
        self.mock_url_for = self.patch_url_for.start()
        self.mock_json = self.patch_json.start()

        self.checkout_service = CheckoutService()
        
        self.form_data = {
            "payment_method": "BANK_TRANSFER",
            "shipping_cost": 10000
        }
        self.mock_session.clear()

    def tearDown(self):
        self.patch_checkout_validation.stop()
        self.patch_order_creation.stop()
        self.patch_stock_service.stop()
        self.patch_user_service.stop()
        
        self.patch_session.stop()
        self.patch_url_for.stop()
        self.patch_json.stop()
        super().tearDown()

    def test_process_checkout_user_pending_order(self):
        mock_user = {"id": 1, "username": "test"}
        self.mock_user_svc.get_user_by_id.return_value = mock_user
        mock_pending_order = {"id": 99}
        self.mock_validation_svc.check_pending_order.return_value = (
            mock_pending_order
        )
        self.mock_stock_svc.get_held_items_simple.return_value = [{"id": 1}]
        
        result = self.checkout_service.process_checkout(
            1, "session_id", self.form_data, None
        )
        
        self.assertEqual(result["success"], False)
        self.assertIn("payment_page", result["redirect"])
        self.assertIn("99", result["redirect"])
        self.mock_creation_svc.create_order.assert_not_called()

    def test_process_checkout_user_no_address(self):
        mock_user = {"id": 1, "username": "test"}
        self.mock_user_svc.get_user_by_id.return_value = mock_user
        self.mock_validation_svc.check_pending_order.return_value = None
        self.mock_validation_svc.validate_user_address.return_value = False
        
        result = self.checkout_service.process_checkout(
            1, "session_id", self.form_data, None
        )
        
        self.assertEqual(result["success"], False)
        self.assertIn("edit_address", result["redirect"])
        self.mock_creation_svc.create_order.assert_not_called()

    def test_process_checkout_user_success_cod(self):
        mock_user = {
            "id": 1, "username": "test", "email": "a@b.c", "phone": "123",
            "address_line_1": "Street", "city": "City", "province": "Prov",
            "postal_code": "12345"
        }
        self.mock_user_svc.get_user_by_id.return_value = mock_user
        self.mock_validation_svc.check_pending_order.return_value = None
        self.mock_validation_svc.validate_user_address.return_value = True
        
        self.mock_creation_svc.create_order.return_value = {
            "success": True, "order_id": 100
        }
        
        cod_form = self.form_data.copy()
        cod_form["payment_method"] = "COD"
        
        result = self.checkout_service.process_checkout(
            1, "session_id", cod_form, None
        )
        
        self.mock_creation_svc.create_order.assert_called_once()
        self.assertEqual(result["success"], True)
        self.assertIn("order_success", result["redirect"])

    def test_process_checkout_user_success_bank(self):
        mock_user = {
            "id": 1, "username": "test", "email": "a@b.c", "phone": "123",
            "address_line_1": "Street", "city": "City", "province": "Prov",
            "postal_code": "12345"
        }
        self.mock_user_svc.get_user_by_id.return_value = mock_user
        self.mock_validation_svc.check_pending_order.return_value = None
        self.mock_validation_svc.validate_user_address.return_value = True
        
        self.mock_creation_svc.create_order.return_value = {
            "success": True, "order_id": 101
        }
        
        result = self.checkout_service.process_checkout(
            1, "session_id", self.form_data, None
        )
        
        self.mock_creation_svc.create_order.assert_called_once()
        self.assertEqual(result["success"], True)
        self.assertIn("payment_page", result["redirect"])
        self.assertIn("101", result["redirect"])

    def test_process_checkout_guest_email_exists(self):
        guest_form = {
            **self.form_data,
            "email": "exists@mail.com", "full_name": "Guest", "phone": "123",
            "address_line_1": "Street", "city": "City", "province": "Prov",
            "postal_code": "12345"
        }
        self.mock_validation_svc.check_guest_email_exists.return_value = True
        
        result = self.checkout_service.process_checkout(
            None, "session_id", guest_form, '{"1-1": {"quantity": 1}}'
        )
        
        self.assertEqual(result["success"], False)
        self.assertIn("login", result["redirect"])
        self.assertIn("next=/checkout/", result["redirect"])
        self.mock_creation_svc.create_order.assert_not_called()

    def test_process_checkout_guest_success(self):
        guest_form = {
            **self.form_data,
            "email": "new@mail.com", "full_name": "Guest", "phone": "123",
            "address_line_1": "Street", "city": "City", "province": "Prov",
            "postal_code": "12345"
        }
        self.mock_validation_svc.check_guest_email_exists.return_value = False
        self.mock_creation_svc.create_order.return_value = {
            "success": True, "order_id": 102
        }
        
        result = self.checkout_service.process_checkout(
            None, "session_id", guest_form, '{"1-1": {"quantity": 1}}'
        )
        
        self.mock_creation_svc.create_order.assert_called_once()
        self.assertEqual(result["success"], True)
        self.assertIn("payment_page", result["redirect"])
        self.mock_session.__setitem__.assert_called_with("guest_order_id", 102)

    def test_process_checkout_order_creation_fail(self):
        mock_user = {
            "id": 1, "username": "test", "email": "a@b.c", "phone": "123",
            "address_line_1": "Street", "city": "City", "province": "Prov",
            "postal_code": "12345"
        }
        self.mock_user_svc.get_user_by_id.return_value = mock_user
        self.mock_validation_svc.check_pending_order.return_value = None
        self.mock_validation_svc.validate_user_address.return_value = True
        
        self.mock_creation_svc.create_order.return_value = {
            "success": False, "message": "Out of stock"
        }
        
        result = self.checkout_service.process_checkout(
            1, "session_id", self.form_data, None
        )
        
        self.assertEqual(result["success"], False)
        self.assertIn("cart_page", result["redirect"])
        self.assertEqual(result["message"], "Out of stock")