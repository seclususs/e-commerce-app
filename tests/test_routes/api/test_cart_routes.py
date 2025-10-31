import json
from unittest.mock import patch

from flask import url_for

from tests.base_test_case import BaseTestCase


class TestApiCartRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.cart_service_patch = patch(
            "app.routes.api.cart_routes.cart_service"
        )
        self.mock_cart_service = self.cart_service_patch.start()

        self.stock_service_patch = patch(
            "app.routes.api.cart_routes.stock_service"
        )
        self.mock_stock_service = self.stock_service_patch.start()
        
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"

    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_get_guest_cart_items_success(self):

        with self.client.session_transaction() as sess:
            sess.clear()

        self.mock_cart_service.get_guest_cart_details.return_value = [
            {"id": 1}
        ]
        response = self.client.post(
            url_for("api.get_guest_cart_items"),
            json={"cart_items": [{"id": 1}]},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)

    def test_get_user_cart_success(self):
        self.mock_cart_service.get_cart_details.return_value = {"items": []}
        response = self.client.get(url_for("api.get_user_cart"))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("items", data)

    def test_add_to_user_cart_success(self):
        self.mock_cart_service.add_to_cart.return_value = {"success": True}
        response = self.client.post(
            url_for("api.add_to_user_cart"),
            json={"product_id": 1, "quantity": 1},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])

    def test_add_to_user_cart_out_of_stock(self):
        self.mock_cart_service.add_to_cart.return_value = {
            "success": False, "message": "Stok habis"
        }
        response = self.client.post(
            url_for("api.add_to_user_cart"),
            json={"product_id": 1, "quantity": 99},
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data["success"])

    def test_update_user_cart_item_success(self):
        self.mock_cart_service.update_cart_item.return_value = {"success": True}
        response = self.client.put(
            url_for(
                "api.update_user_cart_item",
                product_id=1,
                variant_id_str="null",
            ),
            json={"quantity": 2},
        )
        self.assertEqual(response.status_code, 200)

    def test_prepare_guest_checkout_success(self):

        with self.client.session_transaction() as sess:
            sess.clear()
        
        with patch("app.routes.api.cart_routes.session", {}) as mock_guest_session:
            self.mock_stock_service.hold_stock_for_checkout.return_value = {
                "success": True,
                "expires_at": "tomorrow",
            }
            response = self.client.post(
                url_for("api.prepare_guest_checkout"),
                json={"items": [{"id": 1, "name": "A", "quantity": 1}]},
            )
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertTrue(data["success"])
            self.assertIn("session_id", mock_guest_session)