from tests.base_test_case import BaseTestCase
from unittest.mock import patch
from decimal import Decimal

from app.services.reports.report_service import ReportService
from app.exceptions.service_exceptions import ServiceLogicError


@patch('app.services.reports.report_service.dashboard_report_service')
@patch('app.services.reports.report_service.sales_report_service')
@patch('app.services.reports.report_service.product_report_service')
@patch('app.services.reports.report_service.customer_report_service')
@patch('app.services.reports.report_service.inventory_report_service')
@patch('app.services.reports.report_service.convert_decimals')
class TestReportService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.report_service = ReportService()
        self.start_date = "2025-01-01"
        self.end_date = "2025-01-31"

    def tearDown(self):
        super().tearDown()

    def test_get_dashboard_stats(
        self, mock_convert, mock_inv, mock_cust, mock_prod,
        mock_sales, mock_dash
    ):
        mock_stats = {"total_sales": Decimal("100")}
        mock_dash.get_dashboard_stats.return_value = mock_stats
        mock_convert.return_value = {"total_sales": 100.0}
        
        result = self.report_service.get_dashboard_stats(
            self.start_date, self.end_date
        )
        
        mock_dash.get_dashboard_stats.assert_called_once_with(
            self.start_date, self.end_date
        )
        mock_convert.assert_called_once_with(mock_stats)
        self.assertEqual(result, {"total_sales": 100.0})

    def test_get_dashboard_stats_error(
        self, mock_convert, mock_inv, mock_cust, mock_prod,
        mock_sales, mock_dash
    ):
        mock_dash.get_dashboard_stats.side_effect = Exception("Error")
        
        with self.assertRaises(ServiceLogicError):
            self.report_service.get_dashboard_stats(
                self.start_date, self.end_date
            )

    def test_get_sales_summary(
        self, mock_convert, mock_inv, mock_cust, mock_prod,
        mock_sales, mock_dash
    ):
        mock_summary = {"total_revenue": 100}
        mock_sales.get_sales_summary.return_value = mock_summary
        
        result = self.report_service.get_sales_summary(
            self.start_date, self.end_date
        )
        
        mock_sales.get_sales_summary.assert_called_once_with(
            self.start_date, self.end_date
        )
        self.assertEqual(result, mock_summary)

    def test_get_sales_summary_error(
        self, mock_convert, mock_inv, mock_cust, mock_prod,
        mock_sales, mock_dash
    ):
        mock_sales.get_sales_summary.side_effect = Exception("Error")
        
        with self.assertRaises(ServiceLogicError):
            self.report_service.get_sales_summary(
                self.start_date, self.end_date
            )

    def test_get_product_reports(
        self, mock_convert, mock_inv, mock_cust, mock_prod,
        mock_sales, mock_dash
    ):
        mock_report = {"top_selling": []}
        mock_prod.get_product_reports.return_value = mock_report
        
        result = self.report_service.get_product_reports(
            self.start_date, self.end_date
        )
        
        mock_prod.get_product_reports.assert_called_once_with(
            self.start_date, self.end_date
        )
        self.assertEqual(result, mock_report)

    def test_get_customer_reports(
        self, mock_convert, mock_inv, mock_cust, mock_prod,
        mock_sales, mock_dash
    ):
        mock_report = {"top_spenders": []}
        mock_cust.get_customer_reports.return_value = mock_report
        
        result = self.report_service.get_customer_reports(
            self.start_date, self.end_date
        )
        
        mock_cust.get_customer_reports.assert_called_once_with(
            self.start_date, self.end_date
        )
        self.assertEqual(result, mock_report)

    def test_get_inventory_reports(
        self, mock_convert, mock_inv, mock_cust, mock_prod,
        mock_sales, mock_dash
    ):
        mock_report = {"total_value": 0}
        mock_inv.get_inventory_reports.return_value = mock_report
        
        result = self.report_service.get_inventory_reports(
            self.start_date, self.end_date
        )
        
        mock_inv.get_inventory_reports.assert_called_once_with(
            self.start_date, self.end_date
        )
        self.assertEqual(result, mock_report)