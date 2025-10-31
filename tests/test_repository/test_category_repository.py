from unittest.mock import MagicMock, patch

from tests.base_test_case import BaseTestCase
from app.repository.category_repository import (
    CategoryRepository, category_repository
)


class TestCategoryRepository(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_cursor = MagicMock()
        patch.object(
            self.db_conn, 'cursor', return_value=self.mock_cursor
        ).start()
        self.repository = CategoryRepository()

    def test_singleton_instance(self):
        self.assertIsInstance(category_repository, CategoryRepository)

    def test_find_all(self):
        mock_result = [{"id": 1, "name": "Category A"}]
        self.mock_cursor.fetchall.return_value = mock_result
        
        result = self.repository.find_all(self.db_conn)

        self.mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM categories ORDER BY name ASC"
        )
        self.assertEqual(result, mock_result)
        self.mock_cursor.close.assert_called_once()

    def test_find_by_id(self):
        mock_result = {"id": 1, "name": "Category A"}
        self.mock_cursor.fetchone.return_value = mock_result
        
        result = self.repository.find_by_id(self.db_conn, 1)

        self.mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM categories WHERE id = %s", (1,)
        )
        self.assertEqual(result, mock_result)
        self.mock_cursor.close.assert_called_once()

    def test_create(self):
        self.mock_cursor.lastrowid = 5
        
        result = self.repository.create(self.db_conn, " New Category ")

        self.mock_cursor.execute.assert_called_once_with(
            "INSERT INTO categories (name) VALUES (%s)", ("New Category",)
        )
        self.assertEqual(result, 5)
        self.mock_cursor.close.assert_called_once()

    def test_update(self):
        self.mock_cursor.rowcount = 1
        
        result = self.repository.update(self.db_conn, 1, " Updated Name ")

        self.mock_cursor.execute.assert_called_once_with(
            "UPDATE categories SET name = %s WHERE id = %s",
            ("Updated Name", 1)
        )
        self.assertEqual(result, 1)
        self.mock_cursor.close.assert_called_once()

    def test_unlink_products(self):
        self.mock_cursor.rowcount = 3
        
        result = self.repository.unlink_products(self.db_conn, 1)

        self.mock_cursor.execute.assert_called_once_with(
            "UPDATE products SET category_id = NULL WHERE category_id = %s",
            (1,)
        )
        self.assertEqual(result, 3)
        self.mock_cursor.close.assert_called_once()

    def test_delete(self):
        self.mock_cursor.rowcount = 1
        
        result = self.repository.delete(self.db_conn, 1)

        self.mock_cursor.execute.assert_called_once_with(
            "DELETE FROM categories WHERE id = %s", (1,)
        )
        self.assertEqual(result, 1)
        self.mock_cursor.close.assert_called_once()