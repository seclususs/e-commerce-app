import unittest
import os
from app import create_app
from app.core.db import get_db_connection
from unittest.mock import patch, MagicMock

class BaseTestCase(unittest.TestCase):
    
    def setUp(self):
        test_config = {
            "TESTING": True,
            "MYSQL_DB": os.environ.get("MYSQL_DB", "ecommerce_db_test"),
            "WTF_CSRF_ENABLED": False,
            "SERVER_NAME": "localhost"
        }
        self.app = create_app(test_config=test_config)
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        self.db_conn = get_db_connection()
        self.cursor = self.db_conn.cursor(dictionary=True)
        self.mock_get_db = patch('app.core.db.get_db_connection').start()
        self.mock_get_db.return_value = self.db_conn
        
        self.patch_service_db_calls('app.services.auth.authentication_service.get_db_connection')
        self.patch_service_db_calls('app.services.auth.password_reset_service.get_db_connection')
        self.patch_service_db_calls('app.services.auth.registration_service.get_db_connection')
        self.patch_service_db_calls('app.services.orders.cart_service.get_db_connection')
        self.patch_service_db_calls('app.services.orders.checkout_service.get_db_connection')
        self.patch_service_db_calls('app.services.orders.checkout_validation_service.get_db_connection')
        self.patch_service_db_calls('app.services.orders.discount_service.get_db_connection')
        self.patch_service_db_calls('app.services.orders.order_cancel_service.get_db_connection')
        self.patch_service_db_calls('app.services.orders.order_creation_service.get_db_connection')
        self.patch_service_db_calls('app.services.orders.order_query_service.get_db_connection')
        self.patch_service_db_calls('app.services.orders.order_update_service.get_db_connection')
        self.patch_service_db_calls('app.services.orders.payment_service.get_db_connection')
        self.patch_service_db_calls('app.services.orders.stock_service.get_db_connection')
        self.patch_service_db_calls('app.services.orders.voucher_service.get_db_connection')
        self.patch_service_db_calls('app.services.products.category_service.get_db_connection')
        self.patch_service_db_calls('app.services.products.product_bulk_service.get_db_connection')
        self.patch_service_db_calls('app.services.products.product_query_service.get_db_connection')
        self.patch_service_db_calls('app.services.products.product_service.get_db_connection')
        self.patch_service_db_calls('app.services.products.review_service.get_db_connection')
        self.patch_service_db_calls('app.services.products.variant_service.get_db_connection')
        self.patch_service_db_calls('app.services.reports.customer_report_service.get_db_connection')
        self.patch_service_db_calls('app.services.reports.dashboard_report_service.get_db_connection')
        self.patch_service_db_calls('app.services.reports.inventory_report_service.get_db_connection')
        self.patch_service_db_calls('app.services.reports.product_report_service.get_db_connection')
        self.patch_service_db_calls('app.services.reports.sales_report_service.get_db_connection')
        self.patch_service_db_calls('app.services.users.user_profile_service.get_db_connection')
        self.patch_service_db_calls('app.services.users.user_service.get_db_connection')
        self.patch_service_db_calls('app.services.utils.scheduler_service.get_db_connection')
        self.patch_service_db_calls('app.services.utils.validation_service.get_db_connection')
        self.patch_service_db_calls('app.services.member.membership_service.get_db_connection')
        self.patch_service_db_calls('app.routes.admin.setting_routes.get_db_connection')
        self.patch_service_db_calls('app.routes.auth.login_routes.get_db_connection')
        self.patch_service_db_calls('app.routes.auth.register_routes.get_db_connection')
        self.patch_service_db_calls('app.routes.purchase.order_routes.get_db_connection')
        self.patch_service_db_calls('app.routes.user.order_routes.get_db_connection')
        self.patch_service_db_calls('app.routes.user.profile_routes.get_db_connection')
        self.patch_service_db_calls('app.routes.product.general_routes.get_db_connection')
        
        self.db_conn.start_transaction = MagicMock()
        self.db_conn.commit = MagicMock(name="mock_commit")
        self.db_conn.rollback = MagicMock(name="mock_service_rollback")


    def patch_service_db_calls(self, path_to_function):
        try:
            mock_patch = patch(path_to_function).start()
            mock_patch.return_value = self.db_conn
        except (ModuleNotFoundError, AttributeError):
            pass

    def tearDown(self):
        patch.stopall()
        
        if self.db_conn and self.db_conn.is_connected():
            self.cursor.close()
            self.db_conn.close()

        self.app_context.pop()