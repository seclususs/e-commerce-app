import json
from unittest.mock import patch

from flask import url_for

from app.exceptions.service_exceptions import ServiceLogicError
from tests.base_test_case import BaseTestCase


class TestAuthForgotPasswordRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.service_patch = patch(
            "app.routes.auth.forgot_password_routes.password_reset_service"
        )
        self.mock_service = self.service_patch.start()

        self.get_content_patch = patch(
            "app.routes.auth.forgot_password_routes.get_content"
        )
        self.mock_get_content = self.get_content_patch.start()
        self.mock_get_content.return_value = {}

    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_forgot_password_get(self):
        response = self.client.get(url_for("auth.forgot_password"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Lupa Password", response.data)

    def test_forgot_password_post_success(self):
        response = self.client.post(
            url_for("auth.forgot_password"),
            data={"email": "test@example.com"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.startswith(url_for("auth.login", _external=False)))
        self.mock_service.handle_password_reset_request.assert_called_once_with(
            "test@example.com"
        )
        
        response = self.client.get(response.location, follow_redirects=True)
        self.assertIn(b"SIMULASI: Jika email terdaftar, link reset password telah dikirim.", response.data)

    def test_forgot_password_post_ajax_success(self):
        response = self.client.post(
            url_for("auth.forgot_password"),
            data={"email": "test@example.com"},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIn("link reset password telah dikirim", data["message"])

    def test_forgot_password_post_no_email(self):
        response = self.client.post(
            url_for("auth.forgot_password"), 
            data={},
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(response.status_code, 400)
        data = response.json
        self.assertFalse(data["success"])
        self.assertIn("Email harus diisi", data["message"])

    def test_forgot_password_post_service_error(self):
        self.mock_service.handle_password_reset_request.side_effect = (
            ServiceLogicError("Service Error")
        )
        response = self.client.post(
            url_for("auth.forgot_password"),
            data={"email": "error@example.com"},
        )
        self.assertEqual(response.status_code, 302)
        response = self.client.get(response.location, follow_redirects=True)
        self.assertIn(b"Terjadi kesalahan saat memproses permintaan.", response.data)