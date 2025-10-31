import json
from unittest.mock import patch

from flask import url_for

from app.exceptions.database_exceptions import DatabaseException
from tests.base_test_case import BaseTestCase


class TestProductCatalogRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.query_service_patch = patch(
            "app.routes.product.catalog_routes.product_query_service"
        )
        self.mock_query_service = self.query_service_patch.start()

        self.category_service_patch = patch(
            "app.routes.product.catalog_routes.category_service"
        )
        self.mock_category_service = self.category_service_patch.start()

        self.get_content_patch = patch(
            "app.routes.product.catalog_routes.get_content"
        )
        self.mock_get_content = self.get_content_patch.start()
        self.mock_get_content.return_value = {"app_name": "Test App"}

    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_products_page_get_success(self):
        mock_product = {
            "id": 1, 
            "name": "Test Product",
            "stock": 10,
            "price": 10000,
            "discount_price": 8000,
            "image_url": "test.jpg",
            "category_name": "Test Category",
            "sizes": "M, L",
            "has_variants": False
        }
        self.mock_query_service.get_filtered_products.return_value = [
            mock_product
        ]
        self.mock_category_service.get_all_categories.return_value = [
            {"id": 1, "name": "Test Category"}
        ]
        response = self.client.get(url_for("product.products_page"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Product", response.data)
        self.assertIn(b"Test Category", response.data)

    def test_products_page_get_ajax_success(self):
        self.mock_query_service.get_filtered_products.return_value = []
        self.mock_category_service.get_all_categories.return_value = []
        response = self.client.get(
            url_for("product.products_page"),
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIn("html", data)

    def test_products_page_get_db_error(self):
        self.mock_query_service.get_filtered_products.side_effect = (
            DatabaseException("DB Error")
        )
        response = self.client.get(url_for("product.products_page"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Gagal memuat produk.", response.data)