import json
from unittest.mock import patch, MagicMock

from flask import url_for

from app.exceptions.api_exceptions import ValidationError
from tests.base_test_case import BaseTestCase


class TestAuthRegisterRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.service_patch = patch(
            "app.routes.auth.register_routes.registration_service"
        )
        self.mock_service = self.service_patch.start()
        
        self.user_service_patch = patch(
            "app.routes.user.profile_routes.user_service"
        )
        self.mock_user_service = self.user_service_patch.start()

        self.get_content_patch = patch(
            "app.routes.auth.register_routes.get_content"
        )
        self.mock_get_content = self.get_content_patch.start()
        self.mock_get_content.return_value = {}
        
        self.mock_cursor = MagicMock()
        patch.object(self.db_conn, 'cursor', return_value=self.mock_cursor).start()


    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_register_get(self):
        response = self.client.get(url_for("auth.register"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Pendaftaran", response.data)

    def test_register_post_success(self):
        self.mock_service.register_new_user.return_value = {
            "id": 1,
            "username": "newuser",
            "is_admin": False,
        }
        response = self.client.post(
            url_for("auth.register"),
            data={"username": "newuser", "email": "a@b.c", "password": "pw"},
            follow_redirects=True
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Voucher selamat datang", response.data)

        with self.client.session_transaction() as sess:
            self.assertEqual(sess["user_id"], 1)

    def test_register_post_validation_error(self):
        self.mock_service.register_new_user.side_effect = ValidationError(
            "Username taken"
        )
        response = self.client.post(
            url_for("auth.register"),
            data={"username": "taken", "email": "a@b.c", "password": "pw"},
        )
        self.assertEqual(response.status_code, 302)

        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("user_id"))

    def test_register_from_order_success(self):
        self.mock_service.register_guest_user.return_value = {
            "id": 2,
            "username": "guest_user",
            "is_admin": False,
        }
        order_details = {"email": "guest@b.c", "name": "Guest"}

        self.mock_user_service.get_active_subscription.return_value = None
        
        self.mock_cursor.rowcount = 1
        
        response = self.client.post(
            url_for("auth.register_from_order"),
            data={
                "order_details": json.dumps(order_details),
                "password": "pw",
                "order_id": "100",
            },
            follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Profil Saya", response.data)
        self.assertIn(b"Akun berhasil dibuat! Voucher selamat datang", response.data)

        with self.client.session_transaction() as sess:
            self.assertEqual(sess["user_id"], 2)
            
        self.mock_cursor.execute.assert_any_call(
            "UPDATE orders SET user_id = %s "
            "WHERE id = %s AND user_id IS NULL",
            (2, "100"),
        )