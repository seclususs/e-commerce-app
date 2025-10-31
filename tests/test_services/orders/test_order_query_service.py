from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock

import mysql.connector

from app.services.orders.order_query_service import OrderQueryService
from app.exceptions.database_exceptions import (
    DatabaseException, RecordNotFoundError
)


class TestOrderQueryService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_order_repo = MagicMock()
        self.mock_item_repo = MagicMock()
        
        self.order_query_service = OrderQueryService(
            order_repo=self.mock_order_repo,
            item_repo=self.mock_item_repo
        )
        
        self.filters = {"status": "Dikirim", "search": "Test"}

    def tearDown(self):
        super().tearDown()

    def test_get_filtered_admin_orders_success(self):
        mock_orders = [{"id": 1, "status": "Dikirim"}]
        self.mock_order_repo.find_filtered_admin.return_value = mock_orders
        
        result = self.order_query_service.get_filtered_admin_orders(
            **self.filters
        )

        self.mock_order_repo.find_filtered_admin.assert_called_once_with(
            self.db_conn, self.filters["status"], None, None,
            self.filters["search"]
        )
        self.assertEqual(result, mock_orders)

    def test_get_filtered_admin_orders_db_error(self):
        self.mock_order_repo.find_filtered_admin.side_effect = (
            mysql.connector.Error("DB Error")
        )
        
        with self.assertRaises(DatabaseException):
            self.order_query_service.get_filtered_admin_orders(**self.filters)

    def test_get_order_details_for_admin_success(self):
        mock_order = {"id": 1, "status": "Diproses"}
        mock_items = [{"product_name": "A", "quantity": 1}]
        self.mock_order_repo.find_details_for_admin.return_value = mock_order
        self.mock_item_repo.find_for_admin_detail.return_value = mock_items
        
        order, items = self.order_query_service.get_order_details_for_admin(1)
        
        self.mock_order_repo.find_details_for_admin.assert_called_once_with(
            self.db_conn, 1
        )
        self.mock_item_repo.find_for_admin_detail.assert_called_once_with(
            self.db_conn, 1
        )
        self.assertEqual(order, mock_order)
        self.assertEqual(items, mock_items)

    def test_get_order_details_for_admin_not_found(self):
        self.mock_order_repo.find_details_for_admin.return_value = None
        
        with self.assertRaises(RecordNotFoundError):
            self.order_query_service.get_order_details_for_admin(1)
            
        self.mock_item_repo.find_for_admin_detail.assert_not_called()

    def test_get_order_details_for_invoice_success(self):
        mock_order = {"id": 1, "status": "Selesai"}
        mock_items = [{"product_name": "A", "quantity": 1}]
        self.mock_order_repo.find_details_for_invoice.return_value = (
            mock_order
        )
        self.mock_item_repo.find_for_invoice.return_value = mock_items
        
        order, items = (
            self.order_query_service.get_order_details_for_invoice(1)
        )
        
        self.assertEqual(order, mock_order)
        self.assertEqual(items, mock_items)