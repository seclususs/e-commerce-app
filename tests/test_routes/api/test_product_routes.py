import json
from unittest.mock import patch

from flask import url_for

from app.exceptions.database_exceptions import DatabaseException
from tests.base_test_case import BaseTestCase


class TestApiProductRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.query_service_patch = patch(
            "app.routes.api.product_routes.product_query_service"
        )
        self.mock_query_service = self.query_service_patch.start()

        self.render_patch = patch(
            "app.routes.api.product_routes.render_template"
        )
        self.mock_render = self.render_patch.start()

    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_filter_products_success(self):
        self.mock_query_service.get_filtered_products.return_value = [
            {"id": 1}
        ]
        self.mock_render.return_value = "<div>Product</div>"
        response = self.client.get(
            url_for("api.filter_products"), query_string={"search": "test"}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["html"], "<div>Product</div>")
        self.mock_query_service.get_filtered_products.assert_called_once_with(
            {"search": "test", "category": None, "sort": "popularity"}
        )

    def test_filter_products_service_error(self):
        self.mock_query_service.get_filtered_products.side_effect = (
            DatabaseException("DB Error")
        )
        response = self.client.get(
            url_for("api.filter_products"), query_string={"search": "test"}
        )
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertEqual(data["message"], "Gagal memfilter produk")