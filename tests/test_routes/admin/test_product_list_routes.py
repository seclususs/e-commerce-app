import json
from unittest.mock import patch

from flask import url_for

from app.exceptions.api_exceptions import ValidationError
from tests.base_test_case import BaseTestCase


class TestAdminProductListRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        
        self.login_admin_patch = patch(
            "app.utils.route_decorators.session",
            {"user_id": 1, "is_admin": True, "username": "admin"},
        )
        self.mock_session = self.login_admin_patch.start()

        self.bulk_service_patch = patch(
            "app.routes.admin.product_list_routes.product_bulk_service"
        )
        self.mock_bulk_service = self.bulk_service_patch.start()

        self.product_service_patch = patch(
            "app.routes.admin.product_list_routes.product_service"
        )
        self.mock_product_service = self.product_service_patch.start()

        self.category_service_patch = patch(
            "app.routes.admin.product_list_routes.category_service"
        )
        self.mock_category_service = self.category_service_patch.start()

        self.query_service_patch = patch(
            "app.routes.admin.product_list_routes.product_query_service"
        )
        self.mock_query_service = self.query_service_patch.start()

    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_admin_products_get_success(self):
        self.mock_category_service.get_all_categories.return_value = []
        self.mock_query_service.get_all_products_with_category.return_value = [
            {"id": 1, "name": "Test Product"}
        ]

        response = self.client.get(url_for("admin.admin_products"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Product", response.data)

    def test_admin_products_post_add_product_success(self):
        mock_new_product = {
            "id": 1,
            "name": "New",
            "price": 10000,
            "discount_price": None,
            "stock": 10,
            "sku": "NEW123",
            "has_variants": False,
            "is_active": True,
            "category_id": 1,
            "image_url": "default.jpg"
        }
        self.mock_product_service.create_product.return_value = {
            "success": True,
            "product": mock_new_product,
        }
        self.mock_category_service.get_category_by_id.return_value = {
            "name": "Cat"
        }

        response = self.client.post(
            url_for("admin.admin_products"),
            data={"form_type": "add_product", "name": "New", "price": 10000, "stock": 10, "weight_grams": 100, "category_id": 1},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIn("html", data)

    def test_admin_products_post_add_product_fail(self):
        self.mock_product_service.create_product.side_effect = ValidationError(
            "400 Bad Request: Name required"
        )

        response = self.client.post(
            url_for("admin.admin_products"),
            data={"form_type": "add_product"},
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertIn("Name required", data["message"])

    def test_admin_products_post_bulk_action_success(self):
        self.mock_bulk_service.handle_bulk_product_action.return_value = {
            "success": True,
            "message": "Deleted 1 products.",
        }
            
        response = self.client.post(
            url_for("admin.admin_products"),
            data={
                "form_type": "bulk_action",
                "bulk_action": "delete",
                "product_ids": ["1"],
            },
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["action"], "delete")
        self.assertEqual(data["ids"], ["1"])