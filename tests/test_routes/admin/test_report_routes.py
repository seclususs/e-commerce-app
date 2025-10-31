import json
from unittest.mock import patch
from decimal import Decimal

from flask import url_for, Response

from app.exceptions.database_exceptions import DatabaseException
from tests.base_test_case import BaseTestCase


class TestAdminReportRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.login_admin_patch = patch(
            "app.utils.route_decorators.session",
            {"user_id": 1, "is_admin": True, "username": "admin"},
        )
        self.mock_session = self.login_admin_patch.start()

        self.report_service_patch = patch(
            "app.routes.admin.report_routes.report_service"
        )
        self.mock_report_service = self.report_service_patch.start()

        self.csv_util_patch = patch(
            "app.routes.admin.report_routes.generate_csv_response"
        )
        self.mock_csv_util = self.csv_util_patch.start()
        
        self.mock_reports_data = {
            "sales": {
                "total_revenue": Decimal("1000.00"),
                "total_orders": 10,
                "total_items_sold": 50
            },
            "products": {
                "top_selling": [],
                "most_viewed": []
            },
            "customers": {
                "top_spenders": []
            },
            "voucher_effectiveness": [],
            "cart_analytics": {
                "abandonment_rate": 0.0,
                "carts_created": 0,
                "orders_completed": 0
            },
            "inventory": {
                "total_value": Decimal("50000.00"),
                "low_stock": [],
                "slow_moving": []
            }
        }

        self.mock_report_service.get_sales_summary.return_value = self.mock_reports_data["sales"]
        self.mock_report_service.get_product_reports.return_value = self.mock_reports_data["products"]
        self.mock_report_service.get_customer_reports.return_value = self.mock_reports_data["customers"]
        self.mock_report_service.get_voucher_effectiveness.return_value = self.mock_reports_data["voucher_effectiveness"]
        self.mock_report_service.get_cart_analytics.return_value = self.mock_reports_data["cart_analytics"]
        self.mock_report_service.get_inventory_reports.return_value = self.mock_reports_data["inventory"]

    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_admin_reports_get_success(self):
        response = self.client.get(url_for("admin.admin_reports"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Laporan & Analitik", response.data)

    def test_admin_reports_get_ajax_success(self):
        response = self.client.get(
            url_for("admin.admin_reports"),
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIn("Laporan Penjualan Detail", data["html"])

    def test_admin_reports_get_db_error(self):
        self.mock_report_service.get_sales_summary.side_effect = (
            DatabaseException("DB Error")
        )
        response_non_ajax = self.client.get(url_for("admin.admin_reports"))
        self.assertEqual(response_non_ajax.status_code, 200)
        self.assertIn(b"Gagal memuat data laporan.", response_non_ajax.data)
        response_ajax = self.client.get(
            url_for("admin.admin_reports"),
            headers={"X-Requested-With": "XMLHttpRequest"},
        )
        self.assertEqual(response_ajax.status_code, 500)
        data_ajax = json.loads(response_ajax.data)
        self.assertFalse(data_ajax["success"])
        self.assertIn("Gagal memuat data laporan", data_ajax["message"])


    def test_export_report_sales_success(self):
        self.mock_report_service.get_full_sales_data_for_export.return_value = [
            [1, "data"]
        ]
        self.mock_csv_util.return_value = Response(
            b"csv,data",
            mimetype="text/csv"
        )

        response = self.client.get(url_for("admin.export_report", report_name="sales"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"csv,data")

    def test_export_report_invalid_name(self):
        response = self.client.get(
            url_for("admin.export_report", report_name="invalid")
        )
        self.assertEqual(response.status_code, 404)