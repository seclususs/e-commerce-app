import json
from unittest.mock import patch

from flask import url_for

from tests.base_test_case import BaseTestCase


class TestPurchaseCartRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.get_content_patch = patch(
            "app.routes.purchase.cart_routes.get_content"
        )
        self.mock_get_content = self.get_content_patch.start()
        self.mock_get_content.return_value = {"app_name": "Test App"}

    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_cart_page_get_success(self):
        response = self.client.get(url_for("purchase.cart_page"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Keranjang Belanja", response.data)

    def test_cart_page_get_ajax_success(self):
        response = self.client.get(
            url_for("purchase.cart_page"),
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIn("html", data)
        self.assertIn("Keranjang Belanja", data["page_title"])