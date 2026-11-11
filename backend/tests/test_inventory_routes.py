import os
import sys
import unittest
from datetime import date, datetime, timedelta

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from config import get_db_connection
from utils.auth_tokens import create_access_token


class TestInventoryRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.user1_id = 1
        cls.user2_id = 2
        cls.token1 = create_access_token(cls.user1_id)
        cls.token2 = create_access_token(cls.user2_id)
        cls.headers1 = {
            "Authorization": f"Bearer {cls.token1}",
            "Content-Type": "application/json"
        }
        cls.headers2 = {
            "Authorization": f"Bearer {cls.token2}",
            "Content-Type": "application/json"
        }

    def setUp(self):
        # Clean up inventory created by test users
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM farm_inventory WHERE user_id IN (%s, %s)", (self.user1_id, self.user2_id))
        cur.execute("DELETE FROM notifications WHERE user_id IN (%s, %s) AND unique_key LIKE 'inv_%%'", (self.user1_id, self.user2_id))
        conn.commit()
        cur.close()
        conn.close()

    def tearDown(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM farm_inventory WHERE user_id IN (%s, %s)", (self.user1_id, self.user2_id))
        cur.execute("DELETE FROM notifications WHERE user_id IN (%s, %s) AND unique_key LIKE 'inv_%%'", (self.user1_id, self.user2_id))
        conn.commit()
        cur.close()
        conn.close()

    def test_inventory_crud_success(self):
        """Test creating, reading, updating, and deleting an inventory item."""
        today_str = date.today().strftime("%Y-%m-%d")
        exp_str = (date.today() + timedelta(days=120)).strftime("%Y-%m-%d")

        # 1. CREATE
        payload = {
            "item_name": "Urea Bio-Fertilizer",
            "category": "Fertilizers",
            "quantity": 50.0,
            "unit": "kg",
            "purchase_price": 280.0,
            "purchase_date": today_str,
            "supplier": "Kisan Krishi Kendra",
            "min_threshold": 15.0,
            "expiry_date": exp_str,
            "storage_location": "Shed 1 Shelf B",
            "notes": "Granular nitrogen fertilizer"
        }
        res = self.client.post("/api/inventory", headers=self.headers1, json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        item_id = data["item_id"]
        self.assertIsNotNone(item_id)

        # 2. READ SINGLE
        res = self.client.get(f"/api/inventory/{item_id}", headers=self.headers1)
        self.assertEqual(res.status_code, 200)
        item_data = res.get_json()["data"]
        self.assertEqual(item_data["item_name"], "Urea Bio-Fertilizer")
        self.assertEqual(item_data["quantity"], 50.0)
        self.assertEqual(item_data["unit"], "kg")
        self.assertEqual(item_data["purchase_price"], 280.0)
        self.assertEqual(item_data["min_threshold"], 15.0)
        self.assertEqual(item_data["stock_status"], "in_stock")
        # Check initial movement was automatically recorded
        self.assertGreaterEqual(len(item_data["recent_movements"]), 1)
        self.assertEqual(item_data["recent_movements"][0]["movement_type"], "Purchase / Addition")

        # 3. LIST / FILTER
        res = self.client.get("/api/inventory?category=Fertilizers", headers=self.headers1)
        self.assertEqual(res.status_code, 200)
        list_data = res.get_json()
        self.assertEqual(list_data["total"], 1)
        self.assertEqual(list_data["data"][0]["id"], item_id)

        # 4. UPDATE
        update_payload = {
            "item_name": "Urea Bio-Fertilizer (Grade A)",
            "min_threshold": 20.0,
            "storage_location": "Main Barn"
        }
        res = self.client.put(f"/api/inventory/{item_id}", headers=self.headers1, json=update_payload)
        self.assertEqual(res.status_code, 200)
        res = self.client.get(f"/api/inventory/{item_id}", headers=self.headers1)
        self.assertEqual(res.get_json()["data"]["item_name"], "Urea Bio-Fertilizer (Grade A)")
        self.assertEqual(res.get_json()["data"]["min_threshold"], 20.0)
        self.assertEqual(res.get_json()["data"]["storage_location"], "Main Barn")

        # 5. DELETE
        res = self.client.delete(f"/api/inventory/{item_id}", headers=self.headers1)
        self.assertEqual(res.status_code, 200)
        res = self.client.get(f"/api/inventory/{item_id}", headers=self.headers1)
        self.assertEqual(res.status_code, 404)

    def test_inventory_validation_errors(self):
        """Test input validation for inventory creation."""
        # Missing item name
        res = self.client.post("/api/inventory", headers=self.headers1, json={"quantity": 10})
        self.assertEqual(res.status_code, 400)
        self.assertIn("Item name is required", res.get_json()["message"])

        # Negative quantity
        res = self.client.post("/api/inventory", headers=self.headers1, json={
            "item_name": "Test Item",
            "quantity": -5.0
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("non-negative", res.get_json()["message"])

        # Negative price
        res = self.client.post("/api/inventory", headers=self.headers1, json={
            "item_name": "Test Item",
            "quantity": 10,
            "purchase_price": -100
        })
        self.assertEqual(res.status_code, 400)

        # Negative min threshold
        res = self.client.post("/api/inventory", headers=self.headers1, json={
            "item_name": "Test Item",
            "quantity": 10,
            "min_threshold": -2
        })
        self.assertEqual(res.status_code, 400)

    def test_stock_movement_purchase_and_audit(self):
        """Test adding stock via Purchase / Addition movement."""
        # Create item with 10 kg
        res = self.client.post("/api/inventory", headers=self.headers1, json={
            "item_name": "Neem Oil Extract",
            "category": "Pesticides",
            "quantity": 10.0,
            "unit": "litre",
            "purchase_price": 450.0
        })
        item_id = res.get_json()["item_id"]

        # Add 15 litres via movement
        mov_res = self.client.post(f"/api/inventory/{item_id}/movement", headers=self.headers1, json={
            "movement_type": "Purchase / Addition",
            "quantity": 15.0,
            "reason": "Restocked new batch",
            "movement_date": date.today().strftime("%Y-%m-%d")
        })
        self.assertEqual(mov_res.status_code, 201)
        mov_data = mov_res.get_json()
        self.assertEqual(mov_data["new_quantity"], 25.0)

        # Verify item quantity updated
        item_res = self.client.get(f"/api/inventory/{item_id}", headers=self.headers1)
        self.assertEqual(item_res.get_json()["data"]["quantity"], 25.0)

        # Verify movements history
        hist_res = self.client.get(f"/api/inventory/{item_id}/movements", headers=self.headers1)
        self.assertEqual(hist_res.status_code, 200)
        movements = hist_res.get_json()["data"]
        self.assertEqual(len(movements), 2)  # Initial purchase + new addition

    def test_stock_movement_usage_and_negative_protection(self):
        """Test consuming stock and verify strict prevention of negative stock."""
        # Create item with 20 kg
        res = self.client.post("/api/inventory", headers=self.headers1, json={
            "item_name": "Hybrid Cotton Seeds",
            "category": "Seeds",
            "quantity": 20.0,
            "unit": "packets",
            "purchase_price": 850.0
        })
        item_id = res.get_json()["item_id"]

        # Try to consume 25 packets (exceeds available 20) -> MUST FAIL 400
        fail_res = self.client.post(f"/api/inventory/{item_id}/movement", headers=self.headers1, json={
            "movement_type": "Usage / Consumption",
            "quantity": 25.0,
            "reason": "Sowing plot A"
        })
        self.assertEqual(fail_res.status_code, 400)
        self.assertIn("Insufficient stock", fail_res.get_json()["message"])

        # Try consuming negative or 0 quantity
        zero_res = self.client.post(f"/api/inventory/{item_id}/movement", headers=self.headers1, json={
            "movement_type": "Usage / Consumption",
            "quantity": 0
        })
        self.assertEqual(zero_res.status_code, 400)

        # Successfully consume 8 packets
        ok_res = self.client.post(f"/api/inventory/{item_id}/movement", headers=self.headers1, json={
            "movement_type": "Usage / Consumption",
            "quantity": 8.0,
            "reason": "Sowing Field 1"
        })
        self.assertEqual(ok_res.status_code, 201)
        self.assertEqual(ok_res.get_json()["new_quantity"], 12.0)

        # Verify item quantity
        item_res = self.client.get(f"/api/inventory/{item_id}", headers=self.headers1)
        self.assertEqual(item_res.get_json()["data"]["quantity"], 12.0)

    def test_stock_movement_damage_and_adjustment(self):
        """Test Damaged/Expired movement and manual inventory Adjustment."""
        res = self.client.post("/api/inventory", headers=self.headers1, json={
            "item_name": "Drip Irrigation Lateral Pipes",
            "category": "Irrigation supplies",
            "quantity": 100.0,
            "unit": "pieces",
            "purchase_price": 55.0
        })
        item_id = res.get_json()["item_id"]

        # Report 5 damaged pieces
        dmg_res = self.client.post(f"/api/inventory/{item_id}/movement", headers=self.headers1, json={
            "movement_type": "Damaged or Expired",
            "quantity": 5.0,
            "reason": "Damaged during transport"
        })
        self.assertEqual(dmg_res.status_code, 201)
        self.assertEqual(dmg_res.get_json()["new_quantity"], 95.0)

        # Stock count adjustment to exactly 90 pieces
        adj_res = self.client.post(f"/api/inventory/{item_id}/movement", headers=self.headers1, json={
            "movement_type": "Adjustment",
            "quantity": 90.0,
            "reason": "Physical warehouse stock audit count"
        })
        self.assertEqual(adj_res.status_code, 201)
        self.assertEqual(adj_res.get_json()["new_quantity"], 90.0)

        # Verify current stock is 90
        item_res = self.client.get(f"/api/inventory/{item_id}", headers=self.headers1)
        self.assertEqual(item_res.get_json()["data"]["quantity"], 90.0)

    def test_inventory_summary_and_low_stock(self):
        """Test summary KPI calculation and low-stock list endpoint."""
        today = date.today()

        # Item 1: Normal stock (50 kg, min 10 kg, ₹100/kg => ₹5,000)
        self.client.post("/api/inventory", headers=self.headers1, json={
            "item_name": "Item A Normal",
            "category": "Fertilizers",
            "quantity": 50.0,
            "unit": "kg",
            "purchase_price": 100.0,
            "min_threshold": 10.0,
            "expiry_date": (today + timedelta(days=90)).strftime("%Y-%m-%d")
        })

        # Item 2: Low stock (4 kg, min 10 kg, ₹200/kg => ₹800)
        self.client.post("/api/inventory", headers=self.headers1, json={
            "item_name": "Item B Low Stock",
            "category": "Pesticides",
            "quantity": 4.0,
            "unit": "litre",
            "purchase_price": 200.0,
            "min_threshold": 10.0,
            "expiry_date": (today + timedelta(days=45)).strftime("%Y-%m-%d")
        })

        # Item 3: Out of stock (0 kg, min 5 kg, ₹50/kg => ₹0)
        self.client.post("/api/inventory", headers=self.headers1, json={
            "item_name": "Item C Out of Stock",
            "category": "Seeds",
            "quantity": 0.0,
            "unit": "packets",
            "purchase_price": 50.0,
            "min_threshold": 5.0
        })

        # Item 4: Expiring soon (10 kg, expires in 7 days, ₹30/kg => ₹300)
        self.client.post("/api/inventory", headers=self.headers1, json={
            "item_name": "Item D Expiring Soon",
            "category": "Herbicides",
            "quantity": 10.0,
            "unit": "kg",
            "purchase_price": 30.0,
            "min_threshold": 5.0,
            "expiry_date": (today + timedelta(days=7)).strftime("%Y-%m-%d")
        })

        # Summary check
        res = self.client.get("/api/inventory/summary", headers=self.headers1)
        self.assertEqual(res.status_code, 200)
        summary = res.get_json()["data"]

        self.assertEqual(summary["total_items"], 4)
        self.assertEqual(summary["low_stock_count"], 1)
        self.assertEqual(summary["out_of_stock_count"], 1)
        self.assertEqual(summary["expiring_soon_count"], 1)
        self.assertEqual(summary["expired_count"], 0)
        # Total valuation = 5000 + 800 + 0 + 300 = 6100.0
        self.assertEqual(summary["total_valuation"], 6100.0)

        # Low-stock endpoint check
        low_res = self.client.get("/api/inventory/low-stock", headers=self.headers1)
        self.assertEqual(low_res.status_code, 200)
        low_items = low_res.get_json()["data"]
        # Should include Item B (low stock) and Item C (out of stock)
        names = [item["item_name"] for item in low_items]
        self.assertIn("Item B Low Stock", names)
        self.assertIn("Item C Out of Stock", names)
        self.assertNotIn("Item A Normal", names)

    def test_inventory_user_data_isolation(self):
        """Ensure User 1 cannot access, modify, or move stock for User 2's inventory."""
        # Create item for User 2
        res2 = self.client.post("/api/inventory", headers=self.headers2, json={
            "item_name": "User 2 Private Tool",
            "category": "Tools and machinery",
            "quantity": 2.0,
            "unit": "pieces",
            "purchase_price": 1200.0
        })
        u2_item_id = res2.get_json()["item_id"]

        # User 1 tries to read User 2's item -> 404
        res1 = self.client.get(f"/api/inventory/{u2_item_id}", headers=self.headers1)
        self.assertEqual(res1.status_code, 404)

        # User 1 tries to update User 2's item -> 404
        up_res1 = self.client.put(f"/api/inventory/{u2_item_id}", headers=self.headers1, json={"quantity": 99})
        self.assertEqual(up_res1.status_code, 404)

        # User 1 tries to add movement to User 2's item -> 404
        mov_res1 = self.client.post(f"/api/inventory/{u2_item_id}/movement", headers=self.headers1, json={
            "movement_type": "Usage / Consumption",
            "quantity": 1.0
        })
        self.assertEqual(mov_res1.status_code, 404)

        # User 1 tries to delete User 2's item -> 404
        del_res1 = self.client.delete(f"/api/inventory/{u2_item_id}", headers=self.headers1)
        self.assertEqual(del_res1.status_code, 404)

        # Verify User 2's item remains intact
        item_check = self.client.get(f"/api/inventory/{u2_item_id}", headers=self.headers2)
        self.assertEqual(item_check.status_code, 200)
        self.assertEqual(item_check.get_json()["data"]["quantity"], 2.0)

    def test_unauthenticated_requests(self):
        """Requests without JWT must return 401 Unauthorized."""
        res = self.client.get("/api/inventory")
        self.assertEqual(res.status_code, 401)
        res = self.client.post("/api/inventory", json={"item_name": "Test"})
        self.assertEqual(res.status_code, 401)
        res = self.client.get("/api/inventory/summary")
        self.assertEqual(res.status_code, 401)


if __name__ == "__main__":
    unittest.main()
