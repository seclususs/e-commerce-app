import json
from unittest.mock import patch

from flask import url_for

from tests.base_test_case import BaseTestCase


class TestAdminVariantRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.login_admin_patch = patch(
            "app.utils.route_decorators.session",
            {"user_id": 1, "is_admin": True, "username": "admin"},
        )
        self.mock_session = self.login_admin_patch.start()

        self.query_service_patch = patch(
            "app.routes.admin.variant_routes.product_query_service"
        )
        self.mock_query_service = self.query_service_patch.start()

        self.variant_service_patch = patch(
            "app.routes.admin.variant_routes.variant_service"
        )
        self.mock_variant_service = self.variant_service_patch.start()

        self.mock_product = {
            "id": 1,
            "name": "Test Product",
            "has_variants": True,
        }

    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_manage_variants_get_success(self):
        self.mock_query_service.get_product_by_id.return_value = (
            self.mock_product
        )
        self.mock_variant_service.get_variants_for_product.return_value = [
            {"id": 10, "size": "M"}
        ]
        response = self.client.get(
            url_for("admin.manage_variants", product_id=1)
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Product", response.data)
        self.assertIn(b"M", response.data)

    def test_manage_variants_get_no_variant_product(self):
        self.mock_product["has_variants"] = False
        self.mock_query_service.get_product_by_id.return_value = (
            self.mock_product
        )
        response = self.client.get(
            url_for("admin.manage_variants", product_id=1)
        )
        self.assertEqual(response.status_code, 302)

    def test_manage_variants_post_add_success(self):
        self.mock_variant_service.add_variant.return_value = {
            "success": True,
            "data": {"id": 11, "size": "L"},
        }
        self.mock_query_service.get_product_by_id.return_value = (
            self.mock_product
        )
        response = self.client.post(
            url_for("admin.manage_variants", product_id=1),
            data={"action": "add", "size": "L", "stock": 10},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIn("html", data)

    def test_manage_variants_post_update_success(self):
        self.mock_variant_service.update_variant.return_value = {
            "success": True
        }
        response = self.client.post(
            url_for("admin.manage_variants", product_id=1),
            data={"action": "update", "variant_id": 10, "size": "XL"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])

    def test_delete_variant_post_success(self):
        self.mock_variant_service.delete_variant.return_value = {
            "success": True
        }
        response = self.client.post(
            url_for("admin.delete_variant", product_id=1, variant_id=10)
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])