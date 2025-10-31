from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock, patch
from decimal import Decimal

import mysql.connector

from app.services.reports.dashboard_report_service import (
    DashboardReportService, convert_decimals
)
from app.exceptions.database_exceptions import DatabaseException


class TestDashboardReportService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_report_repo = MagicMock()

        self.patch_sales_svc = patch(
            'app.services.reports.dashboard_report_service.sales_report_service'
        )
        self.patch_product_svc = patch(
            'app.services.reports.dashboard_report_service.product_report_service'
        )
        self.patch_inventory_svc = patch(
            'app.services.reports.dashboard_report_service.inventory_report_service'
        )
        
        self.mock_sales_svc = self.patch_sales_svc.start()
        self.mock_product_svc = self.patch_product_svc.start()
        self.mock_inventory_svc = self.patch_inventory_svc.start()
        
        self.dashboard_report_service = DashboardReportService(
            report_repo=self.mock_report_repo
        )
        
        self.start_date = "2025-01-01"
        self.end_date = "2025-01-31"

    def tearDown(self):
        self.patch_sales_svc.stop()
        self.patch_product_svc.stop()
        self.patch_inventory_svc.stop()
        super().tearDown()
        
    def test_get_dashboard_stats_success(self):
        self.mock_report_repo.get_dashboard_sales.return_value = Decimal("1000")
        self.mock_report_repo.get_dashboard_order_count.return_value = 10
        self.mock_report_repo.get_dashboard_new_user_count.return_value = 5
        self.mock_report_repo.get_dashboard_product_count.return_value = 50
        self.mock_sales_svc.get_sales_chart_data.return_value = (
            {"labels": ["a"], "data": [1]}
        )
        self.mock_product_svc.get_top_products_chart_data.return_value = (
            {"labels": ["b"], "data": [2]}
        )
        self.mock_inventory_svc.get_low_stock_chart_data.return_value = (
            {"labels": ["c"], "data": [3]}
        )
        
        result = self.dashboard_report_service.get_dashboard_stats(
            self.start_date, self.end_date
        )
        
        self.mock_report_repo.get_dashboard_sales.assert_called_once_with(
            self.db_conn, self.start_date, self.end_date
        )
        self.mock_sales_svc.get_sales_chart_data.assert_called_once_with(
            self.start_date, self.end_date, self.db_conn
        )
        
        expected_stats = {
            "total_sales": Decimal("1000"),
            "order_count": 10,
            "new_user_count": 5,
            "product_count": 50,
            "sales_chart_data": {"labels": ["a"], "data": [1]},
            "top_products_chart": {"labels": ["b"], "data": [2]},
            "low_stock_chart": {"labels": ["c"], "data": [3]},
        }
        self.assertEqual(result, expected_stats)

    def test_get_dashboard_stats_db_error(self):
        self.mock_report_repo.get_dashboard_sales.side_effect = (
            mysql.connector.Error("DB Error")
        )
        
        with self.assertRaises(DatabaseException):
            self.dashboard_report_service.get_dashboard_stats(
                self.start_date, self.end_date
            )

    def test_convert_decimals(self):
        data = {
            "total": Decimal("10.5"),
            "items": [
                {"id": 1, "price": Decimal("5.5")},
                {"id": 2, "price": Decimal("5.0")},
            ],
            "name": "test"
        }
        converted = convert_decimals(data)
        expected = {
            "total": 10.5,
            "items": [
                {"id": 1, "price": 5.5},
                {"id": 2, "price": 5.0},
            ],
            "name": "test"
        }
        self.assertEqual(converted, expected)