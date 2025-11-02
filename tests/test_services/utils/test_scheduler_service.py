from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock, ANY

import mysql.connector

from app.services.utils.scheduler_service import SchedulerService
from app.exceptions.database_exceptions import DatabaseException
from app.exceptions.service_exceptions import ServiceLogicError


class TestSchedulerService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_order_repo = MagicMock()
        self.mock_report_repo = MagicMock()
        self.mock_voucher_repo = MagicMock()
        self.mock_user_voucher_repo = MagicMock()
        
        self.scheduler_service = SchedulerService(
            order_repo=self.mock_order_repo,
            report_repo=self.mock_report_repo,
            voucher_repo=self.mock_voucher_repo,
            user_voucher_repo=self.mock_user_voucher_repo
        )

    def tearDown(self):
        super().tearDown()
        
    def test_cancel_expired_pending_orders_success(self):
        expired_orders = [{"id": 1}, {"id": 2}]
        self.mock_order_repo.find_expired_pending_orders.return_value = (
            expired_orders
        )
        
        result = self.scheduler_service.cancel_expired_pending_orders()
        
        self.mock_order_repo.find_expired_pending_orders.assert_called_with(
            self.db_conn, ANY
        )
        self.mock_order_repo.bulk_update_status.assert_called_once_with(
            self.db_conn, [1, 2], "Dibatalkan"
        )
        self.db_conn.commit.assert_called_once()
        self.assertEqual(result, {"success": True, "cancelled_count": 2})

    def test_cancel_expired_pending_orders_no_orders_found(self):
        self.mock_order_repo.find_expired_pending_orders.return_value = []
        
        result = self.scheduler_service.cancel_expired_pending_orders()
        
        self.mock_order_repo.find_expired_pending_orders.assert_called_with(
            self.db_conn, ANY
        )
        self.mock_order_repo.bulk_update_status.assert_not_called()
        self.db_conn.commit.assert_called_once()
        self.assertEqual(result, {"success": True, "cancelled_count": 0})

    def test_cancel_expired_pending_orders_db_error(self):
        self.mock_order_repo.find_expired_pending_orders.side_effect = (
            mysql.connector.Error("DB Error")
        )
        
        with self.assertRaises(DatabaseException):
            self.scheduler_service.cancel_expired_pending_orders()

    def test_cancel_expired_pending_orders_service_logic_error(self):
        self.mock_order_repo.find_expired_pending_orders.side_effect = (
            Exception("Logic Error")
        )

        with self.assertRaises(ServiceLogicError):
            self.scheduler_service.cancel_expired_pending_orders()

    def test_grant_segmented_vouchers_success(self):
        self.mock_report_repo.get_top_spenders_user_ids_by_percentile.return_value = [1, 2]
        self.mock_voucher_repo.find_by_code.return_value = {"id": 10}
        
        result = self.scheduler_service.grant_segmented_vouchers()
        
        self.mock_report_repo.get_top_spenders_user_ids_by_percentile.assert_called_once_with(
            self.db_conn, 0.05, ANY, ANY
        )
        self.mock_voucher_repo.find_by_code.assert_called_once_with(
            self.db_conn, "TOP_SPENDER"
        )
        self.assertEqual(self.mock_user_voucher_repo.create.call_count, 2)
        self.db_conn.commit.assert_called_once()
        self.assertEqual(result, {"success": True, "granted_count": 2})

    def test_grant_segmented_vouchers_no_spenders(self):
        self.mock_report_repo.get_top_spenders_user_ids_by_percentile.return_value = []
        
        result = self.scheduler_service.grant_segmented_vouchers()
        
        self.mock_voucher_repo.find_by_code.assert_not_called()
        self.mock_user_voucher_repo.create.assert_not_called()
        self.db_conn.commit.assert_called_once()
        self.assertEqual(result, {"success": True, "granted_count": 0})

    def test_grant_segmented_vouchers_no_voucher_found(self):
        self.mock_report_repo.get_top_spenders_user_ids_by_percentile.return_value = [1]
        self.mock_voucher_repo.find_by_code.return_value = None
        
        result = self.scheduler_service.grant_segmented_vouchers()
        
        self.mock_user_voucher_repo.create.assert_not_called()
        self.db_conn.commit.assert_called_once()
        self.assertEqual(result, {"success": False, "granted_count": 0})

    def test_grant_segmented_vouchers_handles_integrity_error(self):
        self.mock_report_repo.get_top_spenders_user_ids_by_percentile.return_value = [1, 2]
        self.mock_voucher_repo.find_by_code.return_value = {"id": 10}
        self.mock_user_voucher_repo.create.side_effect = [
            mysql.connector.IntegrityError(), None
        ]
        
        result = self.scheduler_service.grant_segmented_vouchers()
        
        self.assertEqual(self.mock_user_voucher_repo.create.call_count, 2)
        self.db_conn.commit.assert_called_once()
        self.assertEqual(result, {"success": True, "granted_count": 1})