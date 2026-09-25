import os
import unittest
import pos_core

class TestPOSCore(unittest.TestCase):
    def setUp(self):
        self.original_products = pos_core.load_products()
        self.original_settings = pos_core.load_settings()

    def tearDown(self):
        pos_core.save_products(self.original_products)
        pos_core.update_settings(self.original_settings)

    def test_load_products(self):
        products = pos_core.load_products()
        self.assertIsInstance(products, list)
        self.assertGreater(len(products), 0)
        self.assertIn("id", products[0])
        self.assertIn("name", products[0])
        self.assertIn("price", products[0])
        self.assertIn("stock", products[0])
        self.assertIn("barcode", products[0])

    def test_barcode_lookup(self):
        products = pos_core.load_products()
        item = products[0]
        barcode = item["barcode"]
        found = pos_core.find_product_by_barcode(barcode)
        self.assertIsNotNone(found)
        self.assertEqual(found["id"], item["id"])

        # Also lookup by exact ID as fallback
        found_by_id = pos_core.find_product_by_barcode(str(item["id"]))
        self.assertIsNotNone(found_by_id)
        self.assertEqual(found_by_id["id"], item["id"])

    def test_add_and_update_product(self):
        item = pos_core.add_product("Test Matcha Latte", 4.25, 20, "Beverages", barcode="999001")
        self.assertEqual(item["name"], "Test Matcha Latte")
        self.assertEqual(item["price"], 4.25)
        self.assertEqual(item["stock"], 20)
        self.assertEqual(item["barcode"], "999001")

        updated = pos_core.update_product(item["id"], {"stock": 18, "price": 4.50, "barcode": "999002"})
        self.assertEqual(updated["stock"], 18)
        self.assertEqual(updated["price"], 4.50)
        self.assertEqual(updated["barcode"], "999002")

        deleted = pos_core.delete_product(item["id"])
        self.assertTrue(deleted)

    def test_settings_and_tax_config(self):
        updated = pos_core.update_settings({
            "tax_enabled": True,
            "tax_rate": 10.0,
            "tax_name": "Test Tax"
        })
        self.assertTrue(updated["tax_enabled"])
        self.assertEqual(updated["tax_rate"], 10.0)
        self.assertEqual(updated["tax_name"], "Test Tax")

    def test_checkout_with_modifiers_and_tax(self):
        # Configure tax to 10%
        pos_core.update_settings({"tax_enabled": True, "tax_rate": 10.0})

        products = pos_core.load_products()
        test_item = products[0] # e.g. Espresso at $2.50
        base_price = test_item["price"]

        # Add modifier: Oat Milk +$0.50
        cart_payload = [{
            "id": test_item["id"],
            "qty": 2,
            "modifiers": [{"name": "Oat Milk", "price": 0.50}],
            "notes": "Extra hot"
        }]

        # Expected:
        # unit price = base_price + 0.50 = 3.00
        # subtotal = 3.00 * 2 = 6.00
        # tax (10%) = 0.60
        # total_due = 6.60
        expected_subtotal = round((base_price + 0.50) * 2, 2)
        expected_tax = round(expected_subtotal * 0.10, 2)
        expected_total = round(expected_subtotal + expected_tax, 2)

        # Under-tendering should fail
        with self.assertRaises(ValueError):
            pos_core.process_checkout(cart_payload, expected_total - 1.0)

        # Tender payment with change
        tender_amount = round(expected_total + 100.00, 2)
        tx = pos_core.process_checkout(cart_payload, tender_amount)
        self.assertIsNotNone(tx)
        self.assertEqual(tx["subtotal"], expected_subtotal)
        self.assertEqual(tx["tax_amount"], expected_tax)
        self.assertEqual(tx["total_due"], expected_total)
        self.assertEqual(tx["change"], round(tender_amount - expected_total, 2))
        self.assertIn("Oat Milk", tx["receipt_text"])
        self.assertIn("Extra hot", tx["receipt_text"])
        self.assertIn("Cashier:", tx["receipt_text"])

    def test_analytics(self):
        stats = pos_core.get_analytics()
        self.assertIn("total_revenue", stats)
        self.assertIn("transaction_count", stats)
        self.assertIn("total_sku_count", stats)


if __name__ == "__main__":
    unittest.main()
