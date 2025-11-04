import json
from unittest.mock import patch, MagicMock
from decimal import Decimal

from flask import url_for

from app.exceptions.api_exceptions import ValidationError
from tests.base_test_case import BaseTestCase


class TestUserMembershipRoutes(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.get_content_patch = patch(
            "app.routes.user.membership_routes.get_content"
        )
        self.mock_get_content = self.get_content_patch.start()
        self.mock_get_content.return_value = {"app_name": "Test App"}

        self.membership_service_patch = patch(
            "app.routes.user.membership_routes.membership_service"
        )
        self.mock_membership_service = self.membership_service_patch.start()

        self.user_service_patch = patch(
            "app.routes.user.membership_routes.user_service"
        )
        self.mock_user_service = self.user_service_patch.start()

        self.registration_service_patch = patch(
            "app.routes.user.membership_routes.registration_service"
        )
        self.mock_reg_service = self.registration_service_patch.start()
        
        self.mock_cursor = MagicMock()
        patch.object(self.db_conn, 'cursor', return_value=self.mock_cursor).start()

        self.mock_plan = {
            "id": 1, "name": "Gold", "price": Decimal("100000"),
            "period": "monthly", "is_active": True,
            "discount_percent": Decimal("10.00"),
            "free_shipping": False
        }
        self.mock_user = {"id": 1, "username": "test", "is_admin": False}
        
    def tearDown(self):
        patch.stopall()
        super().tearDown()

    def test_membership_page_get_logged_in(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"
        
        self.mock_membership_service.get_all_active_memberships.return_value = [self.mock_plan]
        self.mock_user_service.get_active_subscription.return_value = None
        
        response = self.client.get(url_for("user.membership_page"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Keanggotaan VIP", response.data)
        self.assertIn(b"Gold", response.data)

    def test_membership_page_get_guest(self):
        self.mock_membership_service.get_all_active_memberships.return_value = [self.mock_plan]
        
        response = self.client.get(url_for("user.membership_page"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Keanggotaan VIP", response.data)
        self.assertIn(b"Beli Paket", response.data)

    def test_membership_page_post_subscribe_success(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"
            
        self.mock_membership_service.subscribe_to_plan.return_value = {
            "success": True, "order_id": 101
        }
        
        response = self.client.post(
            url_for("user.membership_page"),
            data={"action": "subscribe", "membership_id": 1},
            headers={"X-Requested-With": "XMLHttpRequest"}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertEqual(
            url_for("purchase.payment_page", order_id=101, _external=False),
            data["redirect_url"]
        )

    def test_membership_page_post_upgrade_success(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["username"] = "test"
            
        self.mock_membership_service.upgrade_subscription.return_value = {
            "success": True, "order_id": 102
        }
        
        response = self.client.post(
            url_for("user.membership_page"),
            data={"action": "upgrade", "membership_id": 2},
            headers={"X-Requested-With": "XMLHttpRequest"}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertEqual(
            url_for("purchase.payment_page", order_id=102, _external=False),
            data["redirect_url"]
        )

    def test_guest_subscribe_page_get_success(self):
        self.mock_membership_service.membership_repository.find_membership_by_id.return_value = self.mock_plan
        response = self.client.get(
            url_for("user.guest_subscribe_page", membership_id=1)
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Buat Akun Anda", response.data)
        self.assertIn(b"Gold", response.data)

    def test_guest_subscribe_submit_success(self):
        self.mock_reg_service.register_new_user.return_value = self.mock_user
        self.mock_membership_service.subscribe_to_plan.return_value = {
            "success": True, "order_id": 101
        }
        
        mock_order = {
            "id": 101,
            "user_id": 1,
            "payment_method": "Virtual Account",
            "status": "Menunggu Pembayaran",
            "total_amount": Decimal("100000"),
            "subtotal": Decimal("100000"),
            "discount_amount": Decimal("0"),
            "shipping_cost": Decimal("0"),
            "voucher_code": None,
            "payment_transaction_id": "sim_123",
            "notes": "MEMBERSHIP_PURCHASE:1"
        }
        self.mock_cursor.fetchone.return_value = mock_order
        self.mock_cursor.fetchall.return_value = []
        
        response = self.client.post(
            url_for("user.guest_subscribe_submit"),
            data={
                "username": "newuser", "email": "a@b.c", "password": "pw",
                "membership_id": 1
            },
            follow_redirects=True
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Selesaikan Pembayaran", response.data)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["user_id"], 1)

    def test_guest_subscribe_submit_validation_error(self):
        self.mock_reg_service.register_new_user.side_effect = ValidationError("Email taken")
        self.mock_membership_service.membership_repository.find_membership_by_id.return_value = self.mock_plan
        
        response = self.client.post(
            url_for("user.guest_subscribe_submit"),
            data={
                "username": "newuser", "email": "a@b.c", "password": "pw",
                "membership_id": 1
            },
            follow_redirects=True
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Buat Akun Anda", response.data)
        self.assertIn(b"Email taken", response.data)

    def test_subscribe_post_api_success(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
        
        self.mock_membership_service.subscribe_to_plan.return_value = {
            "success": True, "order_id": 101
        }
        response = self.client.post(
            url_for("user.subscribe", membership_id=1)
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertEqual(
            url_for("purchase.payment_page", order_id=101, _external=False),
            data["redirect_url"]
        )

    def test_upgrade_post_api_success(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
        
        self.mock_membership_service.upgrade_subscription.return_value = {
            "success": True, "order_id": 102
        }
        response = self.client.post(
            url_for("user.upgrade", membership_id=2)
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertEqual(
            url_for("purchase.payment_page", order_id=102, _external=False),
            data["redirect_url"]
        )