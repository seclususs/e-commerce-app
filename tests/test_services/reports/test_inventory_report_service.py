from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock
from decimal import Decimal

from app.services.reports.inventory_report_service import (
    InventoryReportService
)


class TestInventoryReportService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_report_repo = MagicMock()

        self.inventory_report_service = InventoryReportService(
            report_repo=self.mock_report_repo
        )
        
        self.start_date = "2025-01-01"
        self.end_date = "2025-01-31"

    def tearDown(self):
        super().tearDown()
        
    def test_get_inventory_reports_success(self):
        self.mock_report_repo.get_inventory_total_value.return_value = (
            Decimal("5000")
        )
        self.mock_report_repo.get_inventory_slow_moving.return_value = [
            {"name": "slow", "stock": 100}
        ]
        self.mock_report_repo.get_inventory_low_stock.return_value = [
            {"name": "low", "stock": 1}
        ]
        
        result = self.inventory_report_service.get_inventory_reports(
            self.start_date, self.end_date
        )
        
        self.mock_report_repo.get_inventory_total_value.assert_called_once_with(
            self.db_conn
        )
        self.mock_report_repo.get_inventory_slow_moving.assert_called_once_with(
            self.db_conn, self.start_date, self.end_date
        )
        self.mock_report_repo.get_inventory_low_stock.assert_called_once_with(
            self.db_conn
        )
        
        expected = {
            "total_value": Decimal("5000"),
            "slow_moving": [{"name": "slow", "stock": 100}],
            "low_stock": [{"name": "low", "stock": 1}],
        }
        self.assertEqual(result, expected)

    def test_get_low_stock_chart_data_success(self):
        mock_data = [
            {"name": "Product A", "stock": 2},
            {"name": "Product B", "stock": 1},
        ]
        self.mock_report_repo.get_low_stock_chart_data.return_value = mock_data
        
        result = self.inventory_report_service.get_low_stock_chart_data(
            self.db_conn
        )
        
        self.mock_report_repo.get_low_stock_chart_data.assert_called_once_with(
            self.db_conn
        )
        expected = {
            "labels": ["Product A", "Product B"],
            "data": [2, 1],
        }
        self.assertEqual(result, expected)

    def test_get_inventory_low_stock_for_export_success(self):
        mock_data = [
            {"name": "Product A", "stock": 1, "type": "Varian"}
        ]
        self.mock_report_repo.get_inventory_low_stock_for_export.return_value = (
            mock_data
        )
        
        result = (
            self.inventory_report_service.get_inventory_low_stock_for_export()
        )
        
        self.assertEqual(result, [["Product A", 1, "Varian"]])

    def test_get_inventory_slow_moving_for_export_success(self):
        mock_data = [
            {"name": "Product C", "stock": 50, "total_sold": 0}
        ]
        (
            self.mock_report_repo.
            get_inventory_slow_moving_for_export.return_value
        ) = mock_data
        
        result = (
            self.inventory_report_service.
            get_inventory_slow_moving_for_export(
                self.start_date, self.end_date
            )
        )
        
        self.assertEqual(result, [["Product C", 50, 0]])