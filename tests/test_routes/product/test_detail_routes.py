import json
import datetime
from unittest.mock import patch

from flask import url_for

from app.exceptions.database_exceptions import RecordNotFoundError
from tests.base_test_case import BaseTestCase


class TestProductDetailRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.query_service_patch = patch(
            "app.routes.product.detail_routes.product_query_service"
        )
        self.mock_query_service = self.query_service_patch.start()

        self.review_service_patch = patch(
            "app.routes.product.detail_routes.review_service"
        )
        self.mock_review_service = self.review_service_patch.start()

        self.get_content_patch = patch(
            "app.routes.product.detail_routes.get_content"
        )
        self.mock_get_content = self.get_content_patch.start()
        self.mock_get_content.return_value = {"app_name": "Test App"}
        
    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_product_detail_get_success(self):
        self.mock_query_service.get_product_by_id.return_value = {
            "id": 1,
            "name": "Test Product",
            "stock": 10,
            "all_images": [],
            "price": 10000,
            "discount_price": 0,
            "category_name": "Test",
            "description": "Desc",
            "has_variants": False,
            "variants": []
        }
        self.mock_review_service.get_reviews_for_product.return_value = []
        self.mock_query_service.get_related_products.return_value = []
        response = self.client.get(url_for("product.product_detail", id=1))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Product", response.data)

    def test_product_detail_get_not_found(self):
        self.mock_query_service.get_product_by_id.side_effect = (
            RecordNotFoundError("Not found")
        )
        response = self.client.get(url_for("product.product_detail", id=99))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.startswith(url_for("product.products_page", _external=False)))


    def test_add_review_post_success(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"
        
        self.mock_review_service.add_review.return_value = {
            "success": True,
            "review_id": 1,
            "message": "Ulasan ditambahkan"
        }
        self.mock_review_service.get_review_by_id.return_value = {
            "id": 1,
            "comment": "Great",
            "username": "test",
            "rating": 5,
            "created_at": datetime.datetime.now()
        }
        response = self.client.post(
            url_for("product.add_review", id=1),
            data={"rating": 5, "comment": "Great"},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIn("review_html", data)

    def test_add_review_post_not_logged_in(self):
        response = self.client.post(
            url_for("product.add_review", id=1),
            data={"rating": 5, "comment": "Great"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.startswith(url_for("auth.login", _external=False)))