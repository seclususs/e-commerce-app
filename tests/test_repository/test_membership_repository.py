from decimal import Decimal
from datetime import datetime
from unittest.mock import MagicMock, patch

from tests.base_test_case import BaseTestCase
from app.repository.membership_repository import (
    MembershipRepository, membership_repository
)


class TestMembershipRepository(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_cursor = MagicMock()
        patch.object(
            self.db_conn, 'cursor', return_value=self.mock_cursor
        ).start()
        self.repository = MembershipRepository()
        self.test_data = {
            "name": "Gold", "price": Decimal("100000"), "period": "monthly",
            "discount_percent": 10, "free_shipping": 1,
            "description": "Test", "is_active": 1
        }
        self.start_date = datetime(2025, 1, 1)
        self.end_date = datetime(2025, 2, 1)

    def test_singleton_instance(self):
        self.assertIsInstance(membership_repository, MembershipRepository)

    def test_find_active_subscription_by_user_id(self):
        self.repository.find_active_subscription_by_user_id(self.db_conn, 1)
        self.mock_cursor.execute.assert_called_once()
        query = self.mock_cursor.execute.call_args[0][0]
        params = self.mock_cursor.execute.call_args[0][1]
        self.assertIn("us.user_id = %s", query)
        self.assertIn("us.status = 'active'", query)
        self.assertIn("us.end_date > CURRENT_TIMESTAMP", query)
        self.assertEqual(params, (1,))
        self.mock_cursor.close.assert_called_once()

    def test_find_membership_by_id(self):
        self.repository.find_membership_by_id(self.db_conn, 1)
        self.mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM memberships WHERE id = %s", (1,)
        )
        self.mock_cursor.close.assert_called_once()

    def test_find_all_active_memberships(self):
        self.repository.find_all_active_memberships(self.db_conn)
        self.mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM memberships WHERE is_active = 1 "
            "ORDER BY price"
        )
        self.mock_cursor.close.assert_called_once()

    def test_create_subscription(self):
        self.mock_cursor.lastrowid = 1
        result = self.repository.create_subscription(
            self.db_conn, 1, 2, self.start_date, self.end_date, 'active'
        )
        self.mock_cursor.execute.assert_called_once()
        params = self.mock_cursor.execute.call_args[0][1]
        self.assertEqual(params, (1, 2, self.start_date, self.end_date, 'active'))
        self.assertEqual(result, 1)
        self.mock_cursor.close.assert_called_once()

    def test_update_subscription(self):
        self.mock_cursor.rowcount = 1
        result = self.repository.update_subscription(
            self.db_conn, 5, 2, self.start_date, self.end_date, 'active'
        )
        self.mock_cursor.execute.assert_called_once()
        params = self.mock_cursor.execute.call_args[0][1]
        self.assertEqual(params, (2, self.start_date, self.end_date, 'active', 5))
        self.assertEqual(result, 1)
        self.mock_cursor.close.assert_called_once()

    def test_create_transaction(self):
        self.mock_cursor.lastrowid = 1
        result = self.repository.create_transaction(
            self.db_conn, 1, 2, 'subscribe', Decimal("100000"), 'Notes'
        )
        self.mock_cursor.execute.assert_called_once()
        params = self.mock_cursor.execute.call_args[0][1]
        self.assertEqual(params, (1, 2, 'subscribe', Decimal("100000"), 'Notes'))
        self.assertEqual(result, 1)
        self.mock_cursor.close.assert_called_once()

    def test_create_membership(self):
        self.mock_cursor.lastrowid = 1
        result = self.repository.create_membership(self.db_conn, self.test_data)
        self.mock_cursor.execute.assert_called_once()
        params = self.mock_cursor.execute.call_args[0][1]
        self.assertEqual(params, (
            "Gold", Decimal("100000"), "monthly", 10, 1, "Test", 1
        ))
        self.assertEqual(result, 1)
        self.mock_cursor.close.assert_called_once()

    def test_update_membership(self):
        self.mock_cursor.rowcount = 1
        result = self.repository.update_membership(self.db_conn, 1, self.test_data)
        self.mock_cursor.execute.assert_called_once()
        params = self.mock_cursor.execute.call_args[0][1]
        self.assertEqual(params, (
            "Gold", Decimal("100000"), "monthly", 10, 1, "Test", 1, 1
        ))
        self.assertEqual(result, 1)
        self.mock_cursor.close.assert_called_once()

    def test_find_all_memberships(self):
        self.repository.find_all_memberships(self.db_conn)
        self.mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM memberships ORDER BY price"
        )
        self.mock_cursor.close.assert_called_once()

    def test_delete_membership(self):
        self.mock_cursor.rowcount = 1
        result = self.repository.delete_membership(self.db_conn, 1)
        self.mock_cursor.execute.assert_called_once_with(
            "DELETE FROM memberships WHERE id = %s", (1,)
        )
        self.assertEqual(result, 1)
        self.mock_cursor.close.assert_called_once()