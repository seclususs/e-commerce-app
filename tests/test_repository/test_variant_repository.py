from unittest.mock import MagicMock, patch

from tests.base_test_case import BaseTestCase
from app.repository.variant_repository import (
    VariantRepository, variant_repository
)


class TestVariantRepository(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_cursor = MagicMock()
        patch.object(
            self.db_conn, 'cursor', return_value=self.mock_cursor
        ).start()
        self.repository = VariantRepository()

    def test_singleton_instance(self):
        self.assertIsInstance(variant_repository, VariantRepository)

    def test_find_by_product_id(self):
        self.repository.find_by_product_id(self.db_conn, 1)
        
        self.mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM product_variants "
            "WHERE product_id = %s ORDER BY id",
            (1,)
        )
        self.mock_cursor.close.assert_called_once()

    def test_create(self):
        self.mock_cursor.lastrowid = 10
        
        result = self.repository.create(
            self.db_conn, 1, " m ", 10, 100, "SKU1"
        )

        self.mock_cursor.execute.assert_called_once_with(
            "\n                INSERT INTO product_variants\n"
            "                (product_id, size, stock, weight_grams, sku)\n"
            "                VALUES (%s, %s, %s, %s, %s)\n"
            "                ",
            (1, "M", 10, 100, "SKU1")
        )
        self.assertEqual(result, 10)
        self.mock_cursor.close.assert_called_once()

    def test_update(self):
        self.mock_cursor.rowcount = 1
        
        result = self.repository.update(
            self.db_conn, 10, 1, " l ", 20, 150, "SKU2"
        )

        self.mock_cursor.execute.assert_called_once_with(
            "\n                UPDATE product_variants\n"
            "                SET size = %s, stock = %s, "
            "weight_grams = %s, sku = %s\n"
            "                WHERE id = %s AND product_id = %s\n"
            "                ",
            ("L", 20, 150, "SKU2", 10, 1)
        )
        self.assertEqual(result, 1)
        self.mock_cursor.close.assert_called_once()

    def test_delete(self):
        self.mock_cursor.rowcount = 1
        
        result = self.repository.delete(self.db_conn, 10, 1)

        self.mock_cursor.execute.assert_called_once_with(
            "DELETE FROM product_variants WHERE id = %s AND product_id = %s",
            (10, 1)
        )
        self.assertEqual(result, 1)
        self.mock_cursor.close.assert_called_once()

    def test_delete_by_product_id(self):
        self.mock_cursor.rowcount = 3
        
        result = self.repository.delete_by_product_id(self.db_conn, 1)

        self.mock_cursor.execute.assert_called_once_with(
            "DELETE FROM product_variants WHERE product_id = %s",
            (1,)
        )
        self.assertEqual(result, 3)
        self.mock_cursor.close.assert_called_once()

    def test_get_total_stock_with_stock(self):
        self.mock_cursor.fetchone.return_value = {"total": 30}
        
        result = self.repository.get_total_stock(self.db_conn, 1)

        self.assertEqual(result, 30)
        self.mock_cursor.close.assert_called_once()

    def test_get_total_stock_no_stock(self):
        self.mock_cursor.fetchone.return_value = {"total": None}
        
        result = self.repository.get_total_stock(self.db_conn, 1)

        self.assertEqual(result, 0)
        self.mock_cursor.close.assert_called_once()

    def test_check_exists_true(self):
        self.mock_cursor.fetchone.return_value = (1,)
        
        result = self.repository.check_exists(self.db_conn, 10, 1)

        self.assertTrue(result)
        self.mock_cursor.close.assert_called_once()

    def test_check_exists_false(self):
        self.mock_cursor.fetchone.return_value = None
        
        result = self.repository.check_exists(self.db_conn, 10, 1)

        self.assertFalse(result)
        self.mock_cursor.close.assert_called_once()

    def test_find_batch_minimal_empty(self):
        result = self.repository.find_batch_minimal(self.db_conn, [])
        
        self.assertEqual(result, [])
        self.mock_cursor.execute.assert_not_called()
        self.mock_cursor.close.assert_called_once()

    def test_find_batch_minimal_with_ids(self):
        self.repository.find_batch_minimal(self.db_conn, [10, 11])
        
        self.mock_cursor.execute.assert_called_once_with(
            "SELECT id, product_id, size FROM product_variants "
            "WHERE id IN (%s, %s)",
            (10, 11)
        )
        self.mock_cursor.close.assert_called_once()

    def test_lock_stock(self):
        self.repository.lock_stock(self.db_conn, 10)
        
        self.mock_cursor.execute.assert_called_once_with(
            "SELECT stock FROM product_variants WHERE id = %s FOR UPDATE",
            (10,)
        )
        self.mock_cursor.close.assert_called_once()

    def test_decrease_stock(self):
        self.mock_cursor.rowcount = 1
        
        result = self.repository.decrease_stock(self.db_conn, 10, 2)
        
        self.mock_cursor.execute.assert_called_once_with(
            "UPDATE product_variants SET stock = stock - %s WHERE id = %s",
            (2, 10)
        )
        self.assertEqual(result, 1)
        self.mock_cursor.close.assert_called_once()