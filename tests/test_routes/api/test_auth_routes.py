import json
from unittest.mock import patch

from flask import url_for

from app.exceptions.database_exceptions import DatabaseException
from tests.base_test_case import BaseTestCase


class TestApiAuthRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.validation_service_patch = patch(
            "app.routes.api.auth_routes.validation_service"
        )
        self.mock_validation_service = self.validation_service_patch.start()

    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_validate_username_success_available(self):
        self.mock_validation_service.validate_username_availability.return_value = (
            True,
            "Username tersedia.",
        )
        response = self.client.post(
            url_for("api.validate_username"),
            json={"username": "new_user"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["available"])
        self.assertEqual(data["message"], "Username tersedia.")

    def test_validate_username_success_taken(self):
        self.mock_validation_service.validate_username_availability.return_value = (
            False,
            "Username sudah digunakan.",
        )
        response = self.client.post(
            url_for("api.validate_username"),
            json={"username": "taken_user"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertFalse(data["available"])

    def test_validate_username_no_data(self):
        response = self.client.post(
            url_for("api.validate_username"), json={}
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertIn("Username tidak boleh kosong", data["message"])

    def test_validate_email_success(self):
        self.mock_validation_service.validate_email_availability.return_value = (
            True,
            "Email tersedia.",
        )
        response = self.client.post(
            url_for("api.validate_email"),
            json={"email": "new@email.com"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["available"])

    def test_validate_email_db_error(self):
        self.mock_validation_service.validate_email_availability.side_effect = (
            DatabaseException("DB Error")
        )
        response = self.client.post(
            url_for("api.validate_email"),
            json={"email": "error@email.com"},
        )
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        data = response.json
        self.assertFalse(data["success"])