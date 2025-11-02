from unittest.mock import patch

from flask import url_for

from tests.base_test_case import BaseTestCase


class TestPurchaseCheckoutRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.user_service_patch = patch(
            "app.routes.purchase.checkout_routes.user_service"
        )
        self.mock_user_service = self.user_service_patch.start()

        self.cart_service_patch = patch(
            "app.routes.purchase.checkout_routes.cart_service"
        )
        self.mock_cart_service = self.cart_service_patch.start()

        self.stock_service_patch = patch(
            "app.routes.purchase.checkout_routes.stock_service"
        )
        self.mock_stock_service = self.stock_service_patch.start()

        self.checkout_service_patch = patch(
            "app.routes.purchase.checkout_routes.checkout_service"
        )
        self.mock_checkout_service = self.checkout_service_patch.start()

        self.get_content_patch = patch(
            "app.routes.purchase.checkout_routes.get_content"
        )
        self.mock_get_content = self.get_content_patch.start()
        self.mock_get_content.return_value = {}
        
        self.voucher_service_patch = patch(
            "app.routes.purchase.checkout_routes.voucher_service"
        )
        self.mock_voucher_service = self.voucher_service_patch.start()
        self.mock_voucher_service.get_available_vouchers_for_user.return_value = []
        
    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_checkout_get_logged_in_success(self):
        self.mock_user_service.get_user_by_id.return_value = {"id": 1}
        self.mock_cart_service.get_cart_details.return_value = {"items": [1]}
        self.mock_stock_service.hold_stock_for_checkout.return_value = {
            "success": True,
            "expires_at": "2025-10-31T17:00:00Z"
        }
        
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"
            
        response = self.client.get(url_for("purchase.checkout"))
        self.assertEqual(response.status_code, 200)
        self.mock_voucher_service.get_available_vouchers_for_user.assert_called_with(1)

    def test_checkout_get_logged_in_empty_cart(self):
        self.mock_user_service.get_user_by_id.return_value = {"id": 1}
        self.mock_cart_service.get_cart_details.return_value = {"items": []}
        
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"

        response = self.client.get(url_for("purchase.checkout"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response.location.startswith(url_for("purchase.cart_page", _external=False))
        )
        self.mock_voucher_service.get_available_vouchers_for_user.assert_called_with(1)


    def test_checkout_post_user_success(self):
        self.mock_checkout_service.process_checkout.return_value = {
            "success": True,
            "redirect": url_for("purchase.order_success"),
        }
        
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"
            
        response = self.client.post(
            url_for("purchase.checkout"), data={"payment_method": "COD"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(url_for("purchase.order_success"), response.location)
        self.mock_checkout_service.process_checkout.assert_called_once()


    def test_edit_address_get_success(self):
        self.mock_user_service.get_user_by_id.return_value = {"id": 1}
        
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"
            
        response = self.client.get(url_for("purchase.edit_address"))
        self.assertEqual(response.status_code, 200)

    def test_edit_address_post_success(self):
        self.mock_user_service.update_user_address.return_value = {
            "success": True
        }
        
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"
            
        response = self.client.post(
            url_for("purchase.edit_address"), data={"phone": "123"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response.location.startswith(url_for("purchase.checkout", _external=False))
        )