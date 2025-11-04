import json
from unittest.mock import patch, MagicMock

from flask import url_for

from tests.base_test_case import BaseTestCase


class TestProductGeneralRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.get_content_patch = patch(
            "app.routes.product.general_routes.get_content"
        )
        self.mock_get_content = self.get_content_patch.start()
        self.mock_get_content.return_value = {"app_name": "Test App"}
        self.mock_cursor = MagicMock()
        patch.object(self.db_conn, 'cursor', return_value=self.mock_cursor).start()
        
    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_index_get_not_logged_in(self):
        self.mock_cursor.fetchall.return_value = [
            {"id": 1, "name": "Top Product", "price": 10000, 
             "discount_price": 0, "image_url": "test.jpg", "category": "Test",
             "stock": 10, "has_variants": False}
        ]
        response = self.client.get(url_for("product.index"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Top Product", response.data)

    def test_index_get_logged_in(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"
            
        response = self.client.get(url_for("product.index"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response.location.startswith(url_for("product.products_page", _external=False))
        )

    def test_home_get_logged_in(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"

        response = self.client.get(url_for("product.home"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response.location.startswith(url_for("product.products_page", _external=False))
        )

    def test_home_get_not_logged_in(self):
        response = self.client.get(url_for("product.home"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.startswith(url_for("auth.login", _external=False)))

    def test_about_get_success(self):
        response = self.client.get(url_for("product.about"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Tentang Kami", response.data)

    def test_about_get_ajax_success(self):
        response = self.client.get(
            url_for("product.about"),
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIn("html", data)