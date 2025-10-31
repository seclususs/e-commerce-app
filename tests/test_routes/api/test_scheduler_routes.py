import json
from unittest.mock import patch

from flask import url_for

from app.exceptions.database_exceptions import DatabaseException
from tests.base_test_case import BaseTestCase


class TestApiSchedulerRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.app.config["SECRET_KEY"] = "test_secret"
        self.scheduler_service_patch = patch(
            "app.routes.api.scheduler_routes.scheduler_service"
        )
        self.mock_scheduler_service = self.scheduler_service_patch.start()

    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_run_scheduler_jobs_success(self):
        self.mock_scheduler_service.cancel_expired_pending_orders.return_value = {
            "success": True,
            "cancelled_count": 2,
        }
        response = self.client.post(
            url_for("api.run_scheduler_jobs"),
            headers={"X-API-Key": "test_secret"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["cancelled_count"], 2)

    def test_run_scheduler_jobs_unauthorized(self):
        response = self.client.post(
            url_for("api.run_scheduler_jobs"),
            headers={"X-API-Key": "wrong_key"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn(b"Tidak diizinkan", response.data)

    def test_run_scheduler_jobs_service_error(self):
        self.mock_scheduler_service.cancel_expired_pending_orders.side_effect = (
            DatabaseException("DB Error")
        )
        response = self.client.post(
            url_for("api.run_scheduler_jobs"),
            headers={"X-API-Key": "test_secret"},
        )
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertFalse(data["success"])