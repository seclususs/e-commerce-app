import json
from unittest.mock import patch

from flask import url_for

from app.exceptions.database_exceptions import RecordNotFoundError
from tests.base_test_case import BaseTestCase


class TestAdminCategoryRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.login_admin_patch = patch(
            "app.utils.route_decorators.session",
            {"user_id": 1, "is_admin": True, "username": "admin"},
        )
        self.mock_session = self.login_admin_patch.start()

        self.category_service_patch = patch(
            "app.routes.admin.category_routes.category_service"
        )
        self.mock_category_service = self.category_service_patch.start()

    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_admin_categories_get_success(self):
        self.mock_category_service.get_all_categories.return_value = [
            {"id": 1, "name": "Test Category"}
        ]
        response = self.client.get(url_for("admin.admin_categories"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test Category", response.data)

    def test_admin_categories_post_add_success(self):
        self.mock_category_service.create_category.return_value = {
            "success": True,
            "data": {"id": 2, "name": "New Category"},
        }
        response = self.client.post(
            url_for("admin.admin_categories"),
            data={"action": "add", "name": "New Category"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIn("html", data)

    def test_admin_categories_post_edit_success(self):
        self.mock_category_service.update_category.return_value = {
            "success": True
        }
        response = self.client.post(
            url_for("admin.admin_categories"),
            data={"action": "edit", "id": 1, "name": "Updated Category"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["name"], "Updated Category")

    def test_delete_category_post_success(self):
        self.mock_category_service.delete_category.return_value = {
            "success": True
        }
        response = self.client.post(url_for("admin.delete_category", id=1))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])

    def test_delete_category_post_not_found(self):
        self.mock_category_service.delete_category.side_effect = (
            RecordNotFoundError("Not found")
        )
        response = self.client.post(url_for("admin.delete_category", id=99))
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertFalse(data["success"])