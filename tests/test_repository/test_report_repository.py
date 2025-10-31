from decimal import Decimal
from unittest.mock import MagicMock, patch

from tests.base_test_case import BaseTestCase
from app.repository.report_repository import (
    ReportRepository, report_repository
)


class TestReportRepository(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_cursor = MagicMock()
        self.cursor_patch = patch.object(
            self.db_conn, 'cursor', return_value=self.mock_cursor
        )
        self.cursor_patch.start()
        self.repository = ReportRepository()

    def tearDown(self):
        self.cursor_patch.stop()
        super().tearDown()

    def test_singleton_instance(self):
        self.assertIsInstance(report_repository, ReportRepository)

    def test_get_date_filter_clause_no_dates(self):
        clause, params = self.repository._get_date_filter_clause(
            None, None
        )
        self.assertEqual(
            clause.strip(), "WHERE o.status != 'Dibatalkan'"
        )
        self.assertEqual(params, [])

    def test_get_date_filter_clause_all_dates(self):
        clause, params = self.repository._get_date_filter_clause(
            "2025-01-01", "2025-01-31", table_alias="alias"
        )
        expected_clause = (
            " WHERE alias.status != 'Dibatalkan'"
            " AND alias.order_date >= %s"
            " AND alias.order_date <= %s"
        )
        self.assertEqual(clause, expected_clause)
        self.assertEqual(params, ["2025-01-01", "2025-01-31"])

    def test_get_top_spenders(self):
        self.repository.get_top_spenders(
            self.db_conn, "2025-01-01", "2025-01-31"
        )

        self.mock_cursor.execute.assert_called_once()
        query, params = self.mock_cursor.execute.call_args[0]
        self.assertIn("o.order_date >= %s", query)
        self.assertIn("o.order_date <= %s", query)
        self.assertIn("ORDER BY total_spent DESC", query)
        self.assertEqual(params, ("2025-01-01", "2025-01-31"))
        self.mock_cursor.close.assert_called_once()

    def test_get_dashboard_sales(self):
        mock_result = {"total": Decimal("1000.50")}
        self.mock_cursor.fetchone.return_value = mock_result
        
        result = self.repository.get_dashboard_sales(
            self.db_conn, "2025-01-01", "2025-01-31"
        )

        self.mock_cursor.execute.assert_called_once_with(
            "\n                SELECT SUM(total_amount) AS total\n"
            "                FROM orders\n"
            "                WHERE status != 'Dibatalkan'\n"
            "                AND order_date BETWEEN %s AND %s\n"
            "            ",
            ("2025-01-01", "2025-01-31")
        )
        self.assertEqual(result, Decimal("1000.50"))
        self.mock_cursor.close.assert_called_once()

    def test_get_dashboard_sales_no_result(self):
        mock_result = {"total": None}
        self.mock_cursor.fetchone.return_value = mock_result
        
        result = self.repository.get_dashboard_sales(
            self.db_conn, "2025-01-01", "2025-01-31"
        )
        
        self.assertEqual(result, Decimal("0"))
        self.mock_cursor.close.assert_called_once()

    def test_get_inventory_total_value(self):
        mock_result = {"total_value": Decimal("50000")}
        self.mock_cursor.fetchone.return_value = mock_result
        
        result = self.repository.get_inventory_total_value(self.db_conn)

        self.mock_cursor.execute.assert_called_once()
        query = self.mock_cursor.execute.call_args[0][0]
        self.assertIn("p.has_variants = 0", query)
        self.assertIn("product_variants pv", query)
        self.assertEqual(result, Decimal("50000"))
        self.mock_cursor.close.assert_called_once()

    def test_get_inventory_low_stock(self):
        self.repository.get_inventory_low_stock(self.db_conn)

        self.mock_cursor.execute.assert_called_once()
        query = self.mock_cursor.execute.call_args[0][0]
        self.assertIn("stock <= 5", query)
        self.assertIn("UNION ALL", query)
        self.assertIn("pv.stock <= 5", query)
        self.mock_cursor.close.assert_called_once()

    def test_get_top_selling_products(self):
        self.repository.get_top_selling_products(
            self.db_conn, "2025-01-01", "2025-01-31"
        )

        self.mock_cursor.execute.assert_called_once()
        query, params = self.mock_cursor.execute.call_args[0]
        self.assertIn("SUM(oi.quantity) AS total_sold", query)
        self.assertIn("o.status != 'Dibatalkan'", query)
        self.assertEqual(params, ("2025-01-01", "2025-01-31"))
        self.mock_cursor.close.assert_called_once()

    def test_get_sales_summary(self):
        self.repository.get_sales_summary(
            self.db_conn, "2025-01-01", "2025-01-31"
        )
        
        self.mock_cursor.execute.assert_called_once()
        query, params = self.mock_cursor.execute.call_args[0]
        self.assertIn("COALESCE(SUM(o.total_amount), 0)", query)
        self.assertIn("COUNT(o.id)", query)
        self.assertIn("COALESCE(SUM(oi.quantity), 0)", query)
        self.assertEqual(params, ("2025-01-01", "2025-01-31"))
        self.mock_cursor.close.assert_called_once()

    def test_get_full_vouchers_data_for_export(self):
        self.repository.get_full_vouchers_data_for_export(
            self.db_conn, "2025-01-01", "2025-01-31"
        )
        
        self.mock_cursor.execute.assert_called_once()
        query, params = self.mock_cursor.execute.call_args[0]
        self.assertIn("SELECT COUNT(o.id)", query)
        self.assertIn("SELECT COALESCE(SUM(o.discount_amount), 0)", query)
        self.assertEqual(params, (
            "2025-01-01", "2025-01-31", "2025-01-01", "2025-01-31"
        ))
        self.mock_cursor.close.assert_called_once()