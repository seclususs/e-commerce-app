import json
from unittest.mock import patch

from flask import url_for

from app.exceptions.database_exceptions import DatabaseException
from tests.base_test_case import BaseTestCase


class TestAdminDashboardRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.login_admin_patch = patch(
            "app.utils.route_decorators.session",
            {"user_id": 1, "is_admin": True, "username": "admin"},
        )
        self.mock_session = self.login_admin_patch.start()

        self.report_service_patch = patch(
            "app.routes.admin.dashboard_routes.report_service"
        )
        self.mock_report_service = self.report_service_patch.start()

        self.scheduler_service_patch = patch(
            "app.routes.admin.dashboard_routes.scheduler_service"
        )
        self.mock_scheduler_service = self.scheduler_service_patch.start()

        self.mock_stats = {
            "total_sales": 1000,
            "order_count": 10,
            "new_user_count": 5,
            "product_count": 50,
            "sales_chart_data": {"labels": [], "data": []},
            "top_products_chart": {"labels": [], "data": []},
            "low_stock_chart": {"labels": [], "data": []},
        }

    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_admin_dashboard_get_success(self):
        self.mock_report_service.get_dashboard_stats.return_value = (
            self.mock_stats
        )
        response = self.client.get(url_for("admin.admin_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Dashboard Ringkasan", response.data)

    def test_admin_dashboard_get_ajax_success(self):
        self.mock_report_service.get_dashboard_stats.return_value = (
            self.mock_stats
        )
        response = self.client.get(
            url_for("admin.admin_dashboard"),
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIn("html", data)
        self.assertEqual(data["stats"]["total_sales"], 1000)

    def test_admin_dashboard_get_db_error(self):
        self.mock_report_service.get_dashboard_stats.side_effect = (
            DatabaseException("DB Error")
        )

        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["is_admin"] = True
            sess["username"] = "admin"
        
        response = self.client.get(url_for("admin.admin_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Gagal memuat data dashboard.", response.data)
        ajax_response = self.client.get(
            url_for("admin.admin_dashboard"),
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(ajax_response.status_code, 500)
        data = json.loads(ajax_response.data)
        self.assertFalse(data["success"])
        self.assertIn("Gagal memuat data dashboard", data["message"])


    def test_run_scheduler_post_success(self):
        self.mock_scheduler_service.cancel_expired_pending_orders.return_value = {
            "success": True,
            "cancelled_count": 2,
        }

        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["is_admin"] = True
            sess["username"] = "admin"
            
        response = self.client.post(url_for("admin.run_scheduler"))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIn("2 pesanan", data["message"])