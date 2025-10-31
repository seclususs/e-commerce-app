from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock
from decimal import Decimal

import mysql.connector

from app.services.reports.customer_report_service import CustomerReportService
from app.exceptions.database_exceptions import DatabaseException


class TestCustomerReportService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_report_repo = MagicMock()
        
        self.customer_report_service = CustomerReportService(
            report_repo=self.mock_report_repo
        )

    def tearDown(self):
        super().tearDown()
        
    def test_get_customer_reports_success(self):
        mock_spenders = [{"username": "test", "total_spent": 1000}]
        self.mock_report_repo.get_top_spenders.return_value = mock_spenders
        
        result = self.customer_report_service.get_customer_reports(
            "2025-01-01", "2025-01-31"
        )
        
        self.mock_report_repo.get_top_spenders.assert_called_once_with(
            self.db_conn, "2025-01-01", "2025-01-31"
        )
        self.assertEqual(result, {"top_spenders": mock_spenders})

    def test_get_customer_reports_db_error(self):
        self.mock_report_repo.get_top_spenders.side_effect = (
            mysql.connector.Error("DB Error")
        )
        
        with self.assertRaises(DatabaseException):
            self.customer_report_service.get_customer_reports(
                "2025-01-01", "2025-01-31"
            )

    def test_get_cart_analytics_success(self):
        self.mock_report_repo.get_cart_analytics_created.return_value = 10
        self.mock_report_repo.get_cart_analytics_completed.return_value = 5
        
        result = self.customer_report_service.get_cart_analytics(
            "2025-01-01", "2025-01-31"
        )
        
        self.assertEqual(result, {
            "abandonment_rate": 50.0,
            "carts_created": 10,
            "orders_completed": 5,
        })

    def test_get_cart_analytics_zero_created(self):
        self.mock_report_repo.get_cart_analytics_created.return_value = 0
        self.mock_report_repo.get_cart_analytics_completed.return_value = 0
        
        result = self.customer_report_service.get_cart_analytics(
            "2025-01-01", "2025-01-31"
        )
        
        self.assertEqual(result, {
            "abandonment_rate": 0,
            "carts_created": 0,
            "orders_completed": 0,
        })

    def test_get_full_customers_data_for_export_success(self):
        mock_data = [
            {"id": 1, "username": "test", "total_spent": Decimal("100.50")}
        ]
        self.mock_report_repo.get_full_customers_data_for_export.return_value = (
            mock_data
        )
        
        result = (
            self.customer_report_service.get_full_customers_data_for_export(
                "2025-01-01", "2025-01-31"
            )
        )
        
        self.assertEqual(result, [[1, "test", 100.50]])

    def test_get_full_customers_data_for_export_db_error(self):
        self.mock_report_repo.get_full_customers_data_for_export.side_effect = (
            mysql.connector.Error("DB Error")
        )
        
        with self.assertRaises(DatabaseException):
            (
                self.customer_report_service.
                get_full_customers_data_for_export(
                    "2025-01-01", "2025-01-31"
                )
            )