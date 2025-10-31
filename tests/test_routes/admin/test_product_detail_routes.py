import json
from unittest.mock import patch

from flask import url_for

from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import RecordNotFoundError
from tests.base_test_case import BaseTestCase


class TestAdminProductDetailRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        
        self.product_service_patch = patch(
            "app.routes.admin.product_detail_routes.product_service"
        )
        self.mock_product_service = self.product_service_patch.start()

        self.query_service_patch = patch(
            "app.routes.admin.product_detail_routes.product_query_service"
        )
        self.mock_query_service = self.query_service_patch.start()

        self.category_service_patch = patch(
            "app.routes.admin.product_detail_routes.category_service"
        )
        self.mock_category_service = self.category_service_patch.start()
        
        self.get_content_patch = patch("app.routes.admin.product_detail_routes.get_content")
        self.mock_get_content = self.get_content_patch.start()
        self.mock_get_content.return_value = {}

    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_admin_edit_product_get_success(self):
        self.mock_query_service.get_product_by_id.return_value = {
            "id": 1,
            "name": "Test Product",
            "price": 10000,
            "discount_price": 0,
            "category_id": 1,
            "colors": "Red",
            "has_variants": False,
            "variants": [],
            "stock": 10,
            "weight_grams": 150,
            "sku": "TP-001",
            "description": "Desc",
            "image_url": "test.jpg",
            "additional_image_urls": []
        }
        self.mock_category_service.get_all_categories.return_value = [{"id": 1, "name": "Test Cat"}]

        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["is_admin"] = True

        response = self.client.get(url_for("admin.admin_edit_product", id=1))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Product", response.data)

    def test_admin_edit_product_get_not_found(self):
        self.mock_query_service.get_product_by_id.return_value = None

        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["is_admin"] = True

        response = self.client.get(url_for("admin.admin_edit_product", id=99))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.startswith(url_for("admin.admin_products", _external=False)))


    def test_admin_edit_product_post_success(self):
        self.mock_product_service.update_product.return_value = {
            "success": True
        }

        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["is_admin"] = True

        response = self.client.post(
            url_for("admin.admin_edit_product", id=1),
            data={"name": "Updated"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIn("admin/products", data["redirect_url"])

    def test_admin_edit_product_post_validation_error(self):
        self.mock_product_service.update_product.side_effect = ValidationError(
            "400 Bad Request: Bad data"
        )

        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["is_admin"] = True

        response = self.client.post(
            url_for("admin.admin_edit_product", id=1), 
            data={},
            headers={"X-Requested-With": "XMLHttpRequest"}
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertIn("Bad data", data["message"])

    def test_delete_product_post_success(self):
        self.mock_product_service.delete_product.return_value = {
            "success": True
        }

        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["is_admin"] = True

        response = self.client.post(url_for("admin.delete_product", id=1))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])

    def test_delete_product_post_not_found(self):
        self.mock_product_service.delete_product.side_effect = (
            RecordNotFoundError("Not found")
        )

        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["is_admin"] = True

        response = self.client.post(url_for("admin.delete_product", id=99))
        self.assertEqual(response.status_code, 404)