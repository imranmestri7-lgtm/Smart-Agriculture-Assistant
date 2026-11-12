import os
import sys
import unittest
from datetime import date, datetime, timedelta

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from config import get_db_connection
from utils.auth_tokens import create_access_token


class TestReportRoutes(unittest.TestCase):
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
        # Clean any records specifically created for user2 in tests
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM farm_activities WHERE user_id = %s", (self.user2_id,))
        cur.execute("DELETE FROM farm_expenses WHERE user_id = %s", (self.user2_id,))
        cur.execute("DELETE FROM farm_harvests WHERE user_id = %s", (self.user2_id,))
        cur.execute("DELETE FROM farm_inventory WHERE user_id = %s", (self.user2_id,))
        conn.commit()
        cur.close()
        conn.close()

    def tearDown(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM farm_activities WHERE user_id = %s", (self.user2_id,))
        cur.execute("DELETE FROM farm_expenses WHERE user_id = %s", (self.user2_id,))
        cur.execute("DELETE FROM farm_harvests WHERE user_id = %s", (self.user2_id,))
        cur.execute("DELETE FROM farm_inventory WHERE user_id = %s", (self.user2_id,))
        conn.commit()
        cur.close()
        conn.close()

    def test_unauthenticated_requests(self):
        """All report endpoints must return 401 Unauthorized without JWT."""
        endpoints = [
            "/api/reports/filters-context",
            "/api/reports/overview",
            "/api/reports/crops",
            "/api/reports/disease",
            "/api/reports/irrigation",
            "/api/reports/financial",
            "/api/reports/activities",
            "/api/reports/inventory",
            "/api/reports/alerts"
        ]
        for ep in endpoints:
            res = self.client.get(ep)
            self.assertEqual(res.status_code, 401, f"Expected 401 for {ep}")

    def test_reports_filters_context(self):
        """Test retrieving farms and crops context for filter dropdowns."""
        res = self.client.get("/api/reports/filters-context", headers=self.headers1)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("farms", data)
        self.assertIn("crops", data)
        self.assertIsInstance(data["farms"], list)
        self.assertIsInstance(data["crops"], list)

    def test_farm_overview_report(self):
        """Test overview report structure, metrics and calculations."""
        res = self.client.get("/api/reports/overview?range=last_30_days", headers=self.headers1)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["report_type"], "overview")

        ov = data["data"]
        # Required categories
        self.assertIn("farms", ov)
        self.assertIn("crops", ov)
        self.assertIn("activities", ov)
        self.assertIn("financials", ov)
        self.assertIn("inventory", ov)
        self.assertIn("disease", ov)
        self.assertIn("irrigation", ov)
        self.assertIn("alerts", ov)
        self.assertIn("recent_activities", ov)

        # Check numeric types
        self.assertIsInstance(ov["farms"]["total_farms"], int)
        self.assertIsInstance(ov["crops"]["total_crops"], int)
        self.assertIsInstance(ov["activities"]["total_activities"], int)
        self.assertIsInstance(ov["financials"]["total_expenses"], (int, float))
        self.assertIsInstance(ov["financials"]["total_revenue"], (int, float))
        self.assertIsInstance(ov["financials"]["net_profit"], (int, float))
        self.assertIsInstance(ov["inventory"]["total_items"], int)
        self.assertIsInstance(ov["inventory"]["total_valuation"], (int, float))

    def test_date_range_presets(self):
        """Test date range resolution across presets."""
        presets = [
            ("today", "Today"),
            ("last_7_days", "Last 7 Days"),
            ("last_30_days", "Last 30 Days"),
            ("current_month", None),
            ("previous_month", None),
            ("current_season", "Season"),
            ("all", "All Recorded Time")
        ]
        for preset, expected_substr in presets:
            res = self.client.get(f"/api/reports/overview?range={preset}", headers=self.headers1)
            self.assertEqual(res.status_code, 200, f"Preset {preset} failed")
            data = res.get_json()
            lbl = data["data"]["filters"]["range_label"]
            self.assertTrue(len(lbl) > 0)
            if expected_substr:
                self.assertIn(expected_substr.lower(), lbl.lower())

        # Test Custom range
        res = self.client.get("/api/reports/overview?range=custom&start_date=2026-10-01&end_date=2026-10-31", headers=self.headers1)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertEqual(data["filters"]["start_date"], "2026-10-01")
        self.assertEqual(data["filters"]["end_date"], "2026-10-31")

    def test_crop_management_report(self):
        """Test detailed crops report."""
        res = self.client.get("/api/reports/crops", headers=self.headers1)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["report_type"], "crops")
        crops_data = data["data"]
        self.assertIn("total_crops", crops_data)
        self.assertIn("active_crops", crops_data)
        self.assertIn("harvested_crops", crops_data)
        self.assertIn("status_distribution", crops_data)
        self.assertIn("variety_distribution", crops_data)
        self.assertIn("crops_list", crops_data)

    def test_disease_diagnosis_report(self):
        """Test disease diagnosis reporting endpoint."""
        res = self.client.get("/api/reports/disease", headers=self.headers1)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["report_type"], "disease")
        d = data["data"]
        self.assertIn("total_scans", d)
        self.assertIn("healthy_scans", d)
        self.assertIn("diseased_scans", d)
        self.assertIn("healthy_rate_pct", d)
        self.assertIn("disease_distribution", d)
        self.assertIn("scans_list", d)

    def test_irrigation_report(self):
        """Test irrigation and water usage report."""
        res = self.client.get("/api/reports/irrigation", headers=self.headers1)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["report_type"], "irrigation")
        ir = data["data"]
        self.assertIn("total_records", ir)
        self.assertIn("total_water_applied_mm", ir)
        self.assertIn("total_water_saved_mm", ir)
        self.assertIn("avg_soil_moisture", ir)
        self.assertIn("crop_water_usage", ir)
        self.assertIn("records_list", ir)

    def test_financial_report(self):
        """Test farm financial reports: expenses, revenues, net profit & crop profitability."""
        res = self.client.get("/api/reports/financial", headers=self.headers1)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["report_type"], "financial")
        fin = data["data"]
        self.assertIn("total_expenses", fin)
        self.assertIn("total_revenue", fin)
        self.assertIn("net_profit", fin)
        self.assertIn("profit_margin_pct", fin)
        self.assertIn("expense_categories", fin)
        self.assertIn("buyer_breakdown", fin)
        self.assertIn("crop_profitability", fin)
        self.assertIn("expense_records", fin)
        self.assertIn("harvest_records", fin)

    def test_activities_report(self):
        """Test farm activities and tasks report."""
        res = self.client.get("/api/reports/activities", headers=self.headers1)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["report_type"], "activities")
        act = data["data"]
        self.assertIn("total_activities", act)
        self.assertIn("completed_count", act)
        self.assertIn("pending_count", act)
        self.assertIn("completion_rate_pct", act)
        self.assertIn("category_distribution", act)
        self.assertIn("priority_distribution", act)
        self.assertIn("activities_list", act)

    def test_inventory_report(self):
        """Test farm inventory and stock report."""
        res = self.client.get("/api/reports/inventory", headers=self.headers1)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["report_type"], "inventory")
        inv = data["data"]
        self.assertIn("total_items", inv)
        self.assertIn("total_valuation", inv)
        self.assertIn("low_stock_count", inv)
        self.assertIn("out_of_stock_count", inv)
        self.assertIn("category_breakdown", inv)
        self.assertIn("items_list", inv)
        self.assertIn("movements_list", inv)

    def test_alerts_report(self):
        """Test notifications and alerts report."""
        res = self.client.get("/api/reports/alerts", headers=self.headers1)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["report_type"], "alerts")
        al = data["data"]
        self.assertIn("total_alerts", al)
        self.assertIn("unread_count", al)
        self.assertIn("category_distribution", al)
        self.assertIn("severity_distribution", al)
        self.assertIn("alerts_list", al)

    def test_user_data_isolation(self):
        """Ensure User 1's reports contain zero records from User 2."""
        # Create private records for User 2
        today_str = date.today().strftime("%Y-%m-%d")
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO farm_expenses (user_id, category, amount, expense_date, description)
            VALUES (%s, 'Seeds', 77777.0, %s, 'User 2 Secret Expense')
        """, (self.user2_id, today_str))
        cur.execute("""
            INSERT INTO farm_inventory (user_id, item_name, category, quantity, unit, purchase_price, purchase_date, min_threshold)
            VALUES (%s, 'User 2 Secret Diamond Plow', 'Tools and machinery', 1.0, 'pieces', 99999.0, %s, 1.0)
        """, (self.user2_id, today_str))
        conn.commit()
        cur.close()
        conn.close()

        # Query reports as User 1
        fin_res = self.client.get("/api/reports/financial?range=today", headers=self.headers1)
        self.assertEqual(fin_res.status_code, 200)
        exp_records = fin_res.get_json()["data"]["expense_records"]
        descriptions = [e["description"] for e in exp_records]
        self.assertNotIn("User 2 Secret Expense", descriptions)

        inv_res = self.client.get("/api/reports/inventory", headers=self.headers1)
        self.assertEqual(inv_res.status_code, 200)
        item_names = [i["item_name"] for i in inv_res.get_json()["data"]["items_list"]]
        self.assertNotIn("User 2 Secret Diamond Plow", item_names)


if __name__ == "__main__":
    unittest.main()
