import json
from unittest.mock import patch, MagicMock
import mysql.connector

from flask import url_for

from tests.base_test_case import BaseTestCase


class TestAdminSettingRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.login_admin_patch = patch(
            "app.utils.route_decorators.session",
            {"user_id": 1, "is_admin": True, "username": "admin"},
        )
        self.mock_session = self.login_admin_patch.start()

        self.get_content_patch = patch(
            "app.routes.admin.setting_routes.get_content"
        )
        self.mock_get_content = self.get_content_patch.start()
        self.mock_get_content.return_value = {"app_name": "Test App"}
        
        self.mock_cursor = MagicMock()
        patch.object(self.db_conn, 'cursor', return_value=self.mock_cursor).start()

    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_admin_settings_get_success(self):
        response = self.client.get(url_for("admin.admin_settings"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test App", response.data)
        self.assertIn(b"Pengaturan Konten Website", response.data)

    def test_admin_settings_get_ajax_success(self):
        response = self.client.get(
            url_for("admin.admin_settings"),
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIn("html", data)
        self.assertIn("Test App", data["html"])

    def test_admin_settings_post_success(self):
        response = self.client.post(
            url_for("admin.admin_settings"),
            data={"app_name": "New Name"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIn("berhasil diperbarui", data["message"])
        self.db_conn.commit.assert_called_once()

    def test_admin_settings_post_db_error(self):
        self.mock_cursor.execute.side_effect = mysql.connector.Error("DB Error")
        response = self.client.post(
            url_for("admin.admin_settings"),
            data={"app_name": "New Name"},
        )
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertIn("kesalahan server", data["message"])
        self.db_conn.rollback.assert_called_once()