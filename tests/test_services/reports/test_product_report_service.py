from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock
from decimal import Decimal

import mysql.connector

from app.services.reports.product_report_service import ProductReportService
from app.exceptions.database_exceptions import DatabaseException


class TestProductReportService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_report_repo = MagicMock()
        
        self.product_report_service = ProductReportService(
            report_repo=self.mock_report_repo
        )
        
        self.start_date = "2025-01-01"
        self.end_date = "2025-01-31"

    def tearDown(self):
        super().tearDown()
        
    def test_get_product_reports_success(self):
        mock_selling = [{"name": "A", "total_sold": 10}]
        mock_viewed = [{"name": "B", "popularity": 100}]
        
        self.mock_report_repo.get_top_selling_products.return_value = (
            mock_selling
        )
        self.mock_report_repo.get_most_viewed_products.return_value = (
            mock_viewed
        )
        
        result = self.product_report_service.get_product_reports(
            self.start_date, self.end_date
        )
        
        self.mock_report_repo.get_top_selling_products.assert_called_once_with(
            self.db_conn, self.start_date, self.end_date
        )
        self.mock_report_repo.get_most_viewed_products.assert_called_once_with(
            self.db_conn
        )
        
        expected = {"top_selling": mock_selling, "most_viewed": mock_viewed}
        self.assertEqual(result, expected)

    def test_get_product_reports_db_error(self):
        self.mock_report_repo.get_top_selling_products.side_effect = (
            mysql.connector.Error("DB Error")
        )
        
        with self.assertRaises(DatabaseException):
            self.product_report_service.get_product_reports(
                self.start_date, self.end_date
            )

    def test_get_top_products_chart_data_success(self):
        mock_data = [
            {"name": "Product A", "total_sold": 20},
            {"name": "Product B", "total_sold": 10},
        ]
        (
            self.mock_report_repo.
            get_top_products_chart_data.return_value
        ) = mock_data
        
        result = self.product_report_service.get_top_products_chart_data(
            self.start_date, self.end_date, self.db_conn
        )
        
        self.mock_report_repo.get_top_products_chart_data.assert_called_once_with(
            self.db_conn, self.start_date, self.end_date
        )
        expected = {
            "labels": ["Product A", "Product B"],
            "data": [20, 10],
        }
        self.assertEqual(result, expected)

    def test_get_full_products_data_for_export_success(self):
        mock_data = [
            {"id": 1, "name": "A", "price": Decimal("100.50"), "stock": 10}
        ]
        self.mock_report_repo.get_full_products_data_for_export.return_value = (
            mock_data
        )
        
        result = (
            self.product_report_service.get_full_products_data_for_export(
                self.start_date, self.end_date
            )
        )
        
        self.assertEqual(result, [[1, "A", 100.50, 10]])