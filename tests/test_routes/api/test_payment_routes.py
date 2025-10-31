import json
from unittest.mock import patch

from flask import url_for

from app.exceptions.service_exceptions import OutOfStockError
from tests.base_test_case import BaseTestCase


class TestApiPaymentRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.app.config["SECRET_KEY"] = "test_secret"
        self.payment_service_patch = patch(
            "app.routes.api.payment_routes.payment_service"
        )
        self.mock_payment_service = self.payment_service_patch.start()

    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_payment_webhook_unauthorized(self):
        response = self.client.post(
            url_for("api.payment_webhook"),
            headers={"X-API-Key": "wrong_key"},
        )
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertEqual(data["message"], "Tidak diizinkan")

    def test_payment_webhook_no_data(self):
        response = self.client.post(
            url_for("api.payment_webhook"),
            headers={"X-API-Key": "test_secret"},
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertIn("Payload JSON tidak valid", data["message"])

    def test_payment_webhook_success_event(self):
        self.mock_payment_service.process_successful_payment.return_value = {
            "success": True,
            "message": "Processed",
        }
        payload = {
            "event": "payment_status_update",
            "status": "success",
            "transaction_id": "123",
        }
        response = self.client.post(
            url_for("api.payment_webhook"),
            headers={"X-API-Key": "test_secret"},
            json=payload,
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])

    def test_payment_webhook_other_event(self):
        payload = {"event": "other", "status": "pending"}
        response = self.client.post(
            url_for("api.payment_webhook"),
            headers={"X-API-Key": "test_secret"},
            json=payload,
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIn("diakui", data["message"])

    def test_payment_webhook_service_error(self):
        self.mock_payment_service.process_successful_payment.side_effect = (
            OutOfStockError("Stok habis")
        )
        payload = {
            "event": "payment_status_update",
            "status": "success",
            "transaction_id": "123",
        }
        response = self.client.post(
            url_for("api.payment_webhook"),
            headers={"X-API-Key": "test_secret"},
            json=payload,
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data["success"])
        self.assertEqual(data["message"], "Stok habis")