import json
from unittest.mock import patch, MagicMock
from datetime import datetime

from flask import url_for

from app.exceptions.api_exceptions import AuthError
from tests.base_test_case import BaseTestCase


class TestUserProfileRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()

        self.get_content_patch = patch(
            "app.routes.user.profile_routes.get_content"
        )
        self.mock_get_content = self.get_content_patch.start()
        self.mock_get_content.return_value = {"app_name": "Test App"}

        self.user_service_patch = patch(
            "app.routes.user.profile_routes.user_service"
        )
        self.mock_user_service = self.user_service_patch.start()
        
        self.mock_cursor = MagicMock()
        patch.object(self.db_conn, 'cursor', return_value=self.mock_cursor).start()

    def tearDown(self):
        self.mock_cursor.reset_mock()
        patch.stopall()
        super().tearDown()

    def test_user_profile_get_success(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"
            
        self.mock_cursor.fetchone.return_value = {"id": 1, "username": "test"}
        mock_orders = [
            {
                "id": 100, 
                "status": "Selesai", 
                "order_date": datetime(2025, 1, 1), 
                "total_amount": 50000,
                "tracking_number": "RESI123"
            }
        ]
        self.mock_cursor.fetchall.return_value = mock_orders
        
        response = self.client.get(url_for("user.user_profile"))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Profil Saya", response.data)
        self.assertIn(b"Selesai", response.data)
        self.assertIn(b"RESI123", response.data)

    def test_user_profile_get_user_not_found(self):

        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"

        self.mock_cursor.fetchone.return_value = None
        response = self.client.get(url_for("user.user_profile"))
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))

    def test_edit_profile_get_success(self):

        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"

        self.mock_user_service.get_user_by_id.return_value = {"id": 1}
        response = self.client.get(url_for("user.edit_profile"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Edit Profil", response.data)

    def test_edit_profile_post_update_info_success(self):

        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"

        self.mock_user_service.update_user_info.return_value = {"success": True}
        response = self.client.post(
            url_for("user.edit_profile"),
            data={"form_action": "update_info", "username": "new", "email": "a@b.c"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["username"], "new")

    def test_edit_profile_post_change_password_success(self):

        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"

        self.mock_user_service.change_user_password.return_value = {"success": True}
        response = self.client.post(
            url_for("user.edit_profile"),
            data={
                "form_action": "change_password",
                "current_password": "1",
                "new_password": "2",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])

    def test_edit_profile_post_change_password_auth_error(self):

        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"

        self.mock_user_service.change_user_password.side_effect = AuthError(
            "Wrong pass"
        )
        response = self.client.post(
            url_for("user.edit_profile"),
            data={
                "form_action": "change_password",
                "current_password": "wrong",
                "new_password": "2",
            },
        )
        self.assertEqual(response.status_code, 401)
        data = response.json
        self.assertFalse(data["success"])