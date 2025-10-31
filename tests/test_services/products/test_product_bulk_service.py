from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock

import mysql.connector

from app.services.products.product_bulk_service import ProductBulkService
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import DatabaseException


class TestProductBulkService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_product_repo = MagicMock()
        
        self.product_bulk_service = ProductBulkService(
            product_repo=self.mock_product_repo
        )

    def tearDown(self):
        super().tearDown()

    def test_handle_bulk_delete_success(self):
        selected_ids = [1, 2, 3]
        self.mock_product_repo.delete_batch.return_value = 3
        
        result = self.product_bulk_service.handle_bulk_product_action(
            "delete", selected_ids
        )
        
        self.mock_product_repo.delete_batch.assert_called_once_with(
            self.db_conn, selected_ids
        )
        self.assertEqual(result, {
            "success": True,
            "message": "3 produk berhasil dihapus."
        })

    def test_handle_bulk_set_category_success(self):
        selected_ids = [1, 2]
        category_id = 5
        self.mock_product_repo.update_category_batch.return_value = 2
        
        result = self.product_bulk_service.handle_bulk_product_action(
            "set_category", selected_ids, category_id
        )
        
        (
            self.mock_product_repo.
            update_category_batch.assert_called_once_with(
                self.db_conn, selected_ids, category_id
            )
        )
        self.assertEqual(result, {
            "success": True,
            "message": "Kategori untuk 2 produk berhasil diubah."
        })

    def test_handle_bulk_validation_error_no_action(self):
        with self.assertRaises(ValidationError):
            self.product_bulk_service.handle_bulk_product_action(
                "", [1, 2]
            )

    def test_handle_bulk_validation_error_no_ids(self):
        with self.assertRaises(ValidationError):
            self.product_bulk_service.handle_bulk_product_action(
                "delete", []
            )

    def test_handle_bulk_validation_error_missing_category_id(self):
        with self.assertRaises(ValidationError):
            self.product_bulk_service.handle_bulk_product_action(
                "set_category", [1, 2], None
            )

    def test_handle_bulk_db_error(self):
        self.mock_product_repo.delete_batch.side_effect = (
            mysql.connector.Error("DB Error")
        )
        
        with self.assertRaises(DatabaseException):
            self.product_bulk_service.handle_bulk_product_action(
                "delete", [1, 2]
            )