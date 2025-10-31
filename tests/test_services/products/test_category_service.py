from tests.base_test_case import BaseTestCase
from unittest.mock import MagicMock

import mysql.connector

from app.services.products.category_service import CategoryService
from app.exceptions.api_exceptions import ValidationError
from app.exceptions.database_exceptions import RecordNotFoundError


class TestCategoryService(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_category_repo = MagicMock()
        
        self.category_service = CategoryService(
            category_repo=self.mock_category_repo
        )

    def tearDown(self):
        super().tearDown()

    def test_get_all_categories_success(self):
        mock_categories = [{"id": 1, "name": "Test"}]
        self.mock_category_repo.find_all.return_value = mock_categories
        
        result = self.category_service.get_all_categories()
        
        self.mock_category_repo.find_all.assert_called_once_with(
            self.db_conn
        )
        self.assertEqual(result, mock_categories)

    def test_get_category_by_id_success(self):
        mock_category = {"id": 1, "name": "Test"}
        self.mock_category_repo.find_by_id.return_value = mock_category
        
        result = self.category_service.get_category_by_id(1)
        
        self.mock_category_repo.find_by_id.assert_called_once_with(
            self.db_conn, 1
        )
        self.assertEqual(result, mock_category)

    def test_create_category_success(self):
        self.mock_category_repo.create.return_value = 1
        new_category = {"id": 1, "name": "New Category"}
        self.mock_category_repo.find_by_id.return_value = new_category
        
        result = self.category_service.create_category("New Category")
        
        self.mock_category_repo.create.assert_called_once_with(
            self.db_conn, "New Category"
        )
        self.assertEqual(result, {
            "success": True,
            "message": 'Kategori "New Category" berhasil ditambahkan.',
            "data": new_category
        })

    def test_create_category_validation_error(self):
        with self.assertRaises(ValidationError):
            self.category_service.create_category("  ")

    def test_create_category_integrity_error(self):
        self.mock_category_repo.create.side_effect = (
            mysql.connector.IntegrityError()
        )
        
        result = self.category_service.create_category("Duplicate")
        
        self.assertEqual(result, {
            "success": False,
            "message": 'Kategori "Duplicate" sudah ada.'
        })

    def test_update_category_success(self):
        self.mock_category_repo.update.return_value = 1
        
        result = self.category_service.update_category(1, "Updated Name")
        
        self.mock_category_repo.update.assert_called_once_with(
            self.db_conn, 1, "Updated Name"
        )
        self.assertEqual(result, {
            "success": True,
            "message": "Kategori berhasil diperbarui."
        })

    def test_update_category_not_found(self):
        self.mock_category_repo.update.return_value = 0
        
        with self.assertRaises(RecordNotFoundError):
            self.category_service.update_category(1, "Updated Name")

    def test_delete_category_success(self):
        self.mock_category_repo.delete.return_value = 1
        
        result = self.category_service.delete_category(1)
        
        self.mock_category_repo.unlink_products.assert_called_once_with(
            self.db_conn, 1
        )
        self.mock_category_repo.delete.assert_called_once_with(
            self.db_conn, 1
        )
        self.assertEqual(result, {
            "success": True,
            "message": "Kategori berhasil dihapus."
        })

    def test_delete_category_not_found(self):
        self.mock_category_repo.delete.return_value = 0
        
        with self.assertRaises(RecordNotFoundError):
            self.category_service.delete_category(1)