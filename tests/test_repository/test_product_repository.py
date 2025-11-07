import json
from unittest.mock import MagicMock, patch

from tests.base_test_case import BaseTestCase
from app.repository.product_repository import (
    ProductRepository, product_repository
)


class TestProductRepository(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.mock_cursor = MagicMock()
        self.cursor_patch = patch.object(
            self.db_conn, 'cursor', return_value=self.mock_cursor
        )
        self.cursor_patch.start()
        self.repository = ProductRepository()

    def tearDown(self):
        self.cursor_patch.stop()
        super().tearDown()

    def test_singleton_instance(self):
        self.assertIsInstance(product_repository, ProductRepository)

    def test_find_by_id_with_images(self):
        mock_product = {
            "id": 1, "name": "Test", "additional_image_urls": '["img1.jpg"]'
        }
        self.mock_cursor.fetchone.return_value = mock_product
        
        result = self.repository.find_by_id(self.db_conn, 1)

        self.mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM products WHERE id = %s", (1,)
        )
        self.assertEqual(result["id"], 1)
        self.assertEqual(result["additional_image_urls"], ["img1.jpg"])
        self.mock_cursor.close.assert_called_once()

    def test_find_by_id_invalid_json_images(self):
        mock_product = {
            "id": 1, "name": "Test", "additional_image_urls": 'invalid-json'
        }
        self.mock_cursor.fetchone.return_value = mock_product
        
        result = self.repository.find_by_id(self.db_conn, 1)

        self.assertEqual(result["additional_image_urls"], [])
        self.mock_cursor.close.assert_called_once()

    def test_find_by_id_null_images(self):
        mock_product = {
            "id": 1, "name": "Test", "additional_image_urls": None
        }
        self.mock_cursor.fetchone.return_value = mock_product
        
        result = self.repository.find_by_id(self.db_conn, 1)

        self.assertEqual(result["additional_image_urls"], [])
        self.mock_cursor.close.assert_called_once()

    def test_find_batch_minimal_empty_list(self):
        result = self.repository.find_batch_minimal(self.db_conn, [])
        self.assertEqual(result, [])
        self.mock_cursor.execute.assert_not_called()
        self.mock_cursor.close.assert_called_once()

    def test_find_batch_minimal_with_ids(self):
        mock_result = [{"id": 1}, {"id": 2}]
        self.mock_cursor.fetchall.return_value = mock_result
        
        result = self.repository.find_batch_minimal(self.db_conn, [1, 2])

        self.mock_cursor.execute.assert_called_once_with(
            "SELECT id, name, price, discount_price, image_url, "
            "has_variants FROM products WHERE id IN (%s, %s)",
            (1, 2)
        )
        self.assertEqual(result, mock_result)
        self.mock_cursor.close.assert_called_once()

    def test_find_filtered_sort_price_asc(self):
        self.repository.find_filtered(self.db_conn, {"sort": "price_asc"})
        
        self.mock_cursor.execute.assert_called_once()
        query = self.mock_cursor.execute.call_args[0][0]
        self.assertIn("ORDER BY COALESCE(", query)
        self.assertIn("MIN(COALESCE(pv.discount_price, p.discount_price))", query)
        self.assertIn(") ASC", query)
        self.mock_cursor.close.assert_called_once()

    def test_find_filtered_search_and_category(self):
        filters = {"search": "test", "category": 5}
        
        self.repository.find_filtered(self.db_conn, filters)

        self.mock_cursor.execute.assert_called_once()
        query, params = self.mock_cursor.execute.call_args[0]
        self.assertIn("p.name LIKE %s", query)
        self.assertIn("p.category_id = %s", query)
        self.assertEqual(params, ("%test%", "%test%", "%test%", "%test%", 5))
        self.mock_cursor.close.assert_called_once()

    def test_find_all_with_category_stock_status(self):
        self.repository.find_all_with_category(
            self.db_conn, None, None, "low_stock"
        )
        
        self.mock_cursor.execute.assert_called_once()
        query = self.mock_cursor.execute.call_args[0][0]
        self.assertIn("p.stock > 0 AND p.stock <= 5", query)
        self.mock_cursor.close.assert_called_once()

    def test_delete_batch(self):
        self.mock_cursor.rowcount = 2
        
        result = self.repository.delete_batch(self.db_conn, [1, 2])

        self.mock_cursor.execute.assert_called_once_with(
            "DELETE FROM products WHERE id IN (%s, %s)", (1, 2)
        )
        self.assertEqual(result, 2)
        self.mock_cursor.close.assert_called_once()

    def test_update_category_batch(self):
        self.mock_cursor.rowcount = 2
        
        result = self.repository.update_category_batch(
            self.db_conn, [1, 2], 5
        )

        self.mock_cursor.execute.assert_called_once_with(
            "UPDATE products SET category_id = %s WHERE id IN (%s, %s)",
            (5, 1, 2)
        )
        self.assertEqual(result, 2)
        self.mock_cursor.close.assert_called_once()

    def test_lock_stock(self):
        self.repository.lock_stock(self.db_conn, 1)
        
        self.mock_cursor.execute.assert_called_once_with(
            "SELECT stock FROM products WHERE id = %s FOR UPDATE",
            (1,)
        )
        self.mock_cursor.close.assert_called_once()

    def test_decrease_stock(self):
        self.mock_cursor.rowcount = 1
        
        result = self.repository.decrease_stock(self.db_conn, 1, 2)

        self.mock_cursor.execute.assert_called_once_with(
            "UPDATE products SET stock = stock - %s WHERE id = %s",
            (2, 1)
        )
        self.assertEqual(result, 1)
        self.mock_cursor.close.assert_called_once()