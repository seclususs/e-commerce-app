from unittest.mock import patch

from flask import url_for

from app.exceptions.api_exceptions import AuthError
from tests.base_test_case import BaseTestCase


class TestAuthLoginRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.service_patch = patch(
            "app.routes.auth.login_routes.authentication_service"
        )
        self.mock_service = self.service_patch.start()

        self.get_content_patch = patch("app.routes.auth.login_routes.get_content")
        self.mock_get_content = self.get_content_patch.start()
        self.mock_get_content.return_value = {}

    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_login_get(self):
        response = self.client.get(url_for("auth.login"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Login", response.data) 

    def test_login_get_already_logged_in(self):
        
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"
        
        response = self.client.get(url_for("auth.login"))

        self.assertEqual(response.status_code, 302) # Sekarang harus 302
        self.assertTrue(response.location.startswith(url_for("product.products_page", _external=False)))

    def test_login_post_success_user(self):
        self.mock_service.verify_user_login.return_value = {
            "id": 1,
            "username": "test",
            "is_admin": False,
        }
        response = self.client.post(
            url_for("auth.login"),
            data={"username": "test", "password": "pw"},
        )
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["user_id"], 1)
            self.assertEqual(sess["username"], "test")
            self.assertFalse(sess["is_admin"])

    def test_login_post_success_admin(self):
        self.mock_service.verify_user_login.return_value = {
            "id": 2,
            "username": "admin",
            "is_admin": True,
        }
        response = self.client.post(
            url_for("auth.login"),
            data={"username": "admin", "password": "pw"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.startswith(url_for("admin.admin_dashboard", _external=False)))

    def test_login_post_auth_error(self):
        self.mock_service.verify_user_login.side_effect = AuthError("Wrong pw")
        response = self.client.post(
            url_for("auth.login"),
            data={"username": "test", "password": "wrong"},
        )
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))

    def test_login_post_no_data(self):
        response = self.client.post(url_for("auth.login"), data={})
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))