from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock
from decimal import Decimal
from datetime import datetime

from app.services.reports.sales_report_service import SalesReportService


class TestSalesReportService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_report_repo = MagicMock()
        
        self.sales_report_service = SalesReportService(
            report_repo=self.mock_report_repo
        )
        
        self.start_date = "2025-01-01"
        self.end_date = "2025-01-31"
        self.start_date_dt = "2025-01-01 00:00:00"
        self.end_date_dt = "2025-01-31 23:59:59"

    def tearDown(self):
        super().tearDown()
        
    def test_get_sales_summary_success(self):
        mock_summary = {
            "total_revenue": Decimal("1000"),
            "total_orders": 10,
            "total_items_sold": 50
        }
        self.mock_report_repo.get_sales_summary.return_value = mock_summary
        
        result = self.sales_report_service.get_sales_summary(
            self.start_date, self.end_date
        )
        
        self.mock_report_repo.get_sales_summary.assert_called_once_with(
            self.db_conn, self.start_date, self.end_date
        )
        self.assertEqual(result, mock_summary)

    def test_get_sales_summary_no_data(self):
        self.mock_report_repo.get_sales_summary.return_value = None
        
        result = self.sales_report_service.get_sales_summary(
            self.start_date, self.end_date
        )
        
        expected = {
            "total_revenue": 0,
            "total_orders": 0,
            "total_items_sold": 0,
        }
        self.assertEqual(result, expected)

    def test_get_voucher_effectiveness_success(self):
        mock_data = [{"voucher_code": "TENOFF", "usage_count": 5}]
        self.mock_report_repo.get_voucher_effectiveness.return_value = mock_data
        
        result = self.sales_report_service.get_voucher_effectiveness(
            self.start_date, self.end_date
        )

        self.assertEqual(result, mock_data)

    def test_get_sales_chart_data_success(self):
        mock_data = [
            {"sale_date": datetime(2025, 1, 1).date(), "daily_total": 100},
            {"sale_date": datetime(2025, 1, 3).date(), "daily_total": 200},
        ]
        self.mock_report_repo.get_sales_chart_data.return_value = mock_data
        
        start_dt = "2025-01-01 00:00:00"
        end_dt = "2025-01-03 23:59:59"
        
        result = self.sales_report_service.get_sales_chart_data(
            start_dt, end_dt, self.db_conn
        )
        
        self.mock_report_repo.get_sales_chart_data.assert_called_once_with(
            self.db_conn, start_dt, end_dt
        )
        expected = {
            "labels": ["01 Jan", "02 Jan", "03 Jan"],
            "data": [100.0, 0.0, 200.0],
        }
        self.assertEqual(result, expected)

    def test_get_full_sales_data_for_export_success(self):
        mock_data = [
            {"id": 1, "total_amount": Decimal("100.50"), "status": "Selesai"}
        ]
        self.mock_report_repo.get_full_sales_data_for_export.return_value = (
            mock_data
        )
        
        result = self.sales_report_service.get_full_sales_data_for_export(
            self.start_date, self.end_date
        )
        
        self.assertEqual(result, [[1, 100.50, "Selesai"]])