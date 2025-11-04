from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock, patch
from decimal import Decimal
from datetime import datetime

import mysql.connector

from app.services.member.membership_service import MembershipService
from app.exceptions.api_exceptions import ValidationError

class TestMembershipService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_membership_repo = MagicMock()
        self.mock_order_repo = MagicMock()
        self.mock_user_repo = MagicMock()
        self.mock_history_repo = MagicMock()

        self.patch_uuid = patch(
            'app.services.member.membership_service.uuid.uuid4'
        )
        self.mock_uuid = self.patch_uuid.start()
        self.mock_uuid.return_value.hex = 'TESTUUID123'
        
        self.patch_datetime = patch(
            'app.services.member.membership_service.datetime'
        )
        self.mock_datetime = self.patch_datetime.start()
        self.mock_datetime.now.return_value = datetime(2025, 1, 1)

        self.membership_service = MembershipService(
            membership_repo=self.mock_membership_repo,
            order_repo=self.mock_order_repo,
            user_repo=self.mock_user_repo,
            history_repo=self.mock_history_repo
        )

        self.form_data = {
            "name": "Gold",
            "price": "100000",
            "period": "monthly",
            "discount_percent": "10",
            "free_shipping": "on",
            "is_active": "on",
            "description": "Test"
        }
        self.mock_user = {
            "id": 1, "username": "test", "email": "a@b.c", "phone": "123",
            "address_line_1": "Street", "city": "City", "province": "Prov",
            "postal_code": "12345", "address_line_2": ""
        }
        self.mock_plan = {
            "id": 1, "name": "Gold", "price": Decimal("100000"), 
            "period": "monthly", "is_active": True
        }
        self.mock_subscription = {
            "user_subscription_id": 1, "user_id": 1, "membership_id": 1,
            "name": "Gold", "price": Decimal("100000"), "period": "monthly",
            "start_date": datetime(2025, 1, 1),
            "end_date": datetime(2025, 2, 1)
        }

    def tearDown(self):
        self.patch_uuid.stop()
        self.patch_datetime.stop()
        super().tearDown()

    def test_get_all_memberships_for_admin(self):
        self.mock_membership_repo.find_all_memberships.return_value = [self.mock_plan]
        result = self.membership_service.get_all_memberships_for_admin()
        self.mock_membership_repo.find_all_memberships.assert_called_once_with(self.db_conn)
        self.assertEqual(len(result), 1)

    def test_get_all_active_memberships(self):
        self.mock_membership_repo.find_all_active_memberships.return_value = [self.mock_plan]
        result = self.membership_service.get_all_active_memberships()
        self.mock_membership_repo.find_all_active_memberships.assert_called_once_with(self.db_conn)
        self.assertEqual(len(result), 1)

    def test_create_membership_success(self):
        self.mock_membership_repo.create_membership.return_value = 1
        self.mock_membership_repo.find_membership_by_id.return_value = self.mock_plan
        
        result = self.membership_service.create_membership(self.form_data)
        
        self.mock_membership_repo.create_membership.assert_called_once()
        self.db_conn.commit.assert_called_once()
        self.assertTrue(result["success"])
        self.assertEqual(result["data"], self.mock_plan)

    def test_create_membership_validation_error(self):
        invalid_form = self.form_data.copy()
        invalid_form["price"] = "-100"
        
        with self.assertRaises(ValidationError):
            self.membership_service._validate_and_prepare_data(invalid_form)

    def test_update_membership_success(self):
        self.mock_membership_repo.update_membership.return_value = 1
        self.mock_membership_repo.find_membership_by_id.return_value = self.mock_plan
        
        result = self.membership_service.update_membership(1, self.form_data)
        
        self.mock_membership_repo.update_membership.assert_called_once()
        self.db_conn.commit.assert_called_once()
        self.assertTrue(result["success"])
        self.assertEqual(result["data"], self.mock_plan)

    def test_update_membership_not_found(self):
        self.mock_membership_repo.update_membership.return_value = 0
        
        result = self.membership_service.update_membership(99, self.form_data)
        
        self.db_conn.rollback.assert_called_once()
        self.assertFalse(result["success"])
        self.assertIn("tidak ditemukan", result["message"])

    def test_delete_membership_success(self):
        self.mock_membership_repo.delete_membership.return_value = 1
        result = self.membership_service.delete_membership(1)
        self.mock_membership_repo.delete_membership.assert_called_once_with(self.db_conn, 1)
        self.db_conn.commit.assert_called_once()
        self.assertTrue(result["success"])

    def test_delete_membership_integrity_error(self):
        self.mock_membership_repo.delete_membership.side_effect = mysql.connector.IntegrityError()
        result = self.membership_service.delete_membership(1)
        self.db_conn.rollback.assert_called_once()
        self.assertFalse(result["success"])
        self.assertIn("masih ada pelanggan", result["message"])

    def test_subscribe_to_plan_success(self):
        self.mock_membership_repo.find_active_subscription_by_user_id.return_value = None
        self.mock_membership_repo.find_membership_by_id.return_value = self.mock_plan
        self.mock_user_repo.find_by_id.return_value = self.mock_user
        self.mock_order_repo.create.return_value = 101
        
        result = self.membership_service.subscribe_to_plan(1, 1)

        expected_shipping_details = {
            "name": self.mock_user.get("username"),
            "email": self.mock_user.get("email"),
            "phone": self.mock_user.get("phone", ""),
            "address1": self.mock_user.get("address_line_1", ""),
            "address2": self.mock_user.get("address_line_2", ""),
            "city": self.mock_user.get("city", ""),
            "province": self.mock_user.get("province", ""),
            "postal_code": self.mock_user.get("postal_code", ""),
        }
        
        self.mock_order_repo.create.assert_called_once_with(
            self.db_conn, 1, Decimal("100000"), Decimal("0"), Decimal("0"),
            Decimal("100000"), None, "Virtual Account", "TX-MEM-TESTUUID",
            expected_shipping_details, notes="MEMBERSHIP_PURCHASE:1"
        )
        self.mock_order_repo.update_status.assert_called_once_with(self.db_conn, 101, "Menunggu Pembayaran")
        self.mock_history_repo.create.assert_called_once()
        self.db_conn.commit.assert_called_once()
        self.assertTrue(result["success"])
        self.assertEqual(result["order_id"], 101)

    def test_subscribe_to_plan_already_active(self):
        self.mock_membership_repo.find_active_subscription_by_user_id.return_value = self.mock_subscription
        result = self.membership_service.subscribe_to_plan(1, 1)
        self.db_conn.rollback.assert_called_once()
        self.assertFalse(result["success"])
        self.assertIn("sudah memiliki paket aktif", result["message"])

    def test_upgrade_subscription_success(self):
        mock_yearly_plan = {
            "id": 2, "name": "Platinum", "price": Decimal("1000000"), 
            "period": "yearly", "is_active": True
        }
        self.mock_membership_repo.find_active_subscription_by_user_id.return_value = self.mock_subscription
        self.mock_membership_repo.find_membership_by_id.return_value = mock_yearly_plan
        self.mock_user_repo.find_by_id.return_value = self.mock_user
        self.mock_order_repo.create.return_value = 102
        
        self.mock_datetime.now.return_value = datetime(2025, 1, 16) 
        
        result = self.membership_service.upgrade_subscription(1, 2)
        
        expected_prorated_price = Decimal("1000000") - (Decimal("100000") / Decimal(31) * Decimal(16))
        expected_prorated_price = expected_prorated_price.quantize(Decimal("0.01"))

        expected_shipping_details = {
            "name": self.mock_user.get("username"),
            "email": self.mock_user.get("email"),
            "phone": self.mock_user.get("phone", ""),
            "address1": self.mock_user.get("address_line_1", ""),
            "address2": self.mock_user.get("address_line_2", ""),
            "city": self.mock_user.get("city", ""),
            "province": self.mock_user.get("province", ""),
            "postal_code": self.mock_user.get("postal_code", ""),
        }

        self.mock_order_repo.create.assert_called_once_with(
            self.db_conn, 1, expected_prorated_price, Decimal("0"), Decimal("0"),
            expected_prorated_price, None, "Virtual Account", "TX-UPG-TESTUUID",
            expected_shipping_details, notes="MEMBERSHIP_UPGRADE:2:SUB_ID:1"
        )
        self.db_conn.commit.assert_called_once()
        self.assertTrue(result["success"])
        self.assertEqual(result["order_id"], 102)

    def test_upgrade_subscription_invalid_plan(self):
        self.mock_membership_repo.find_active_subscription_by_user_id.return_value = self.mock_subscription
        self.mock_membership_repo.find_membership_by_id.return_value = self.mock_plan
        
        result = self.membership_service.upgrade_subscription(1, 1)
        
        self.db_conn.rollback.assert_called_once()
        self.assertFalse(result["success"])
        self.assertIn("hanya bisa dilakukan ke paket tahunan", result["message"])

    def test_activate_subscription_from_order(self):
        self.mock_membership_repo.find_membership_by_id.return_value = self.mock_plan
        
        self.membership_service.activate_subscription_from_order(
            self.db_conn, 1, 1, Decimal("100000")
        )
        
        self.mock_membership_repo.create_subscription.assert_called_once_with(
            self.db_conn, 1, 1, datetime(2025, 1, 1), datetime(2025, 2, 1), 'active'
        )
        self.mock_membership_repo.create_transaction.assert_called_once()

    def test_activate_upgrade_from_order(self):
        mock_yearly_plan = {
            "id": 2, "name": "Platinum", "price": Decimal("1000000"), 
            "period": "yearly", "is_active": True
        }
        self.mock_membership_repo.find_active_subscription_by_user_id.return_value = self.mock_subscription
        self.mock_membership_repo.find_membership_by_id.return_value = mock_yearly_plan
        
        self.membership_service.activate_upgrade_from_order(
            self.db_conn, 1, 2, 1, Decimal("950000")
        )
        
        self.mock_membership_repo.update_subscription.assert_called_once_with(
            self.db_conn, 1, 2, datetime(2025, 1, 1), datetime(2026, 1, 1), 'active'
        )
        self.mock_membership_repo.create_transaction.assert_called_once()