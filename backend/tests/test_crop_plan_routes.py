import os
import sys
import unittest
from datetime import date, timedelta

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from config import get_db_connection
from utils.auth_tokens import create_access_token


class TestCropPlanRoutes(unittest.TestCase):
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
        # Clean up crop plans for test users
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM crop_plans WHERE user_id IN (%s, %s)", (self.user1_id, self.user2_id))
        conn.commit()
        cur.close()
        conn.close()

    def tearDown(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM crop_plans WHERE user_id IN (%s, %s)", (self.user1_id, self.user2_id))
        conn.commit()
        cur.close()
        conn.close()

    def test_unauthenticated_requests_rejected(self):
        """Unauthenticated requests must be rejected with 401."""
        endpoints = [
            ("GET", "/api/crop-plans"),
            ("GET", "/api/crop-plans/upcoming"),
            ("GET", "/api/crop-plans/summary"),
            ("GET", "/api/crop-plans/form-context"),
            ("GET", "/api/crop-plans/1"),
            ("POST", "/api/crop-plans"),
            ("PUT", "/api/crop-plans/1"),
            ("DELETE", "/api/crop-plans/1")
        ]
        for method, ep in endpoints:
            if method == "GET":
                res = self.client.get(ep)
            elif method == "POST":
                res = self.client.post(ep, json={})
            elif method == "PUT":
                res = self.client.put(ep, json={})
            elif method == "DELETE":
                res = self.client.delete(ep)
            self.assertEqual(res.status_code, 401, f"Expected 401 for {method} {ep}")

    def test_form_context(self):
        """Form context must return registered farms, crops, seasons, and units."""
        res = self.client.get("/api/crop-plans/form-context", headers=self.headers1)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("farms", data)
        self.assertIn("crops", data)
        self.assertIn("seasons", data)
        self.assertIn("statuses", data)
        self.assertIn("area_units", data)
        self.assertIn("Kharif", data["seasons"])
        self.assertIn("Rabi", data["seasons"])
        self.assertIn("Zaid", data["seasons"])

    def test_create_crop_plan_validation(self):
        """Creating a plan requires valid crop_name, season, dates, and land_area."""
        today = date.today()

        # 1. Missing crop_name
        res = self.client.post("/api/crop-plans", headers=self.headers1, json={
            "season": "Kharif",
            "planned_sowing_date": str(today),
            "expected_harvest_date": str(today + timedelta(days=90)),
            "land_area": 5.0
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("crop_name", res.get_json()["errors"])

        # 2. Invalid season
        res = self.client.post("/api/crop-plans", headers=self.headers1, json={
            "crop_name": "Cotton",
            "season": "SpringSeason",
            "planned_sowing_date": str(today),
            "expected_harvest_date": str(today + timedelta(days=90)),
            "land_area": 5.0
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("season", res.get_json()["errors"])

        # 3. Harvest date earlier than sowing date
        res = self.client.post("/api/crop-plans", headers=self.headers1, json={
            "crop_name": "Cotton",
            "season": "Kharif",
            "planned_sowing_date": str(today),
            "expected_harvest_date": str(today - timedelta(days=10)),
            "land_area": 5.0
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("expected_harvest_date", res.get_json()["errors"])

        # 4. Non-positive land area
        res = self.client.post("/api/crop-plans", headers=self.headers1, json={
            "crop_name": "Cotton",
            "season": "Kharif",
            "planned_sowing_date": str(today),
            "expected_harvest_date": str(today + timedelta(days=90)),
            "land_area": -2.0
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("land_area", res.get_json()["errors"])

    def test_create_and_get_crop_plan(self):
        """Create valid crop plan, retrieve by id and in listing."""
        today = date.today()
        payload = {
            "crop_name": "Soybean / सोयाबीन",
            "variety": "JS-335",
            "season": "Kharif",
            "planned_sowing_date": str(today + timedelta(days=14)),
            "expected_harvest_date": str(today + timedelta(days=110)),
            "land_area": 8.5,
            "area_unit": "acre",
            "target_yield": 85.0,
            "yield_unit": "quintal",
            "estimated_budget": 50000.0,
            "estimated_revenue": 140000.0,
            "status": "Planned",
            "notes": "Rainfed field plot"
        }
        res = self.client.post("/api/crop-plans", headers=self.headers1, json=payload)
        self.assertEqual(res.status_code, 201)
        plan = res.get_json()["plan"]
        plan_id = plan["id"]
        self.assertEqual(plan["crop_name"], "Soybean / सोयाबीन")
        self.assertEqual(plan["variety"], "JS-335")
        self.assertEqual(plan["season"], "Kharif")
        self.assertEqual(plan["land_area"], 8.5)
        self.assertEqual(plan["status"], "Planned")
        self.assertTrue(plan["is_upcoming"])
        self.assertEqual(plan["crop_duration_days"], 96)

        # Retrieve by ID
        res_get = self.client.get(f"/api/crop-plans/{plan_id}", headers=self.headers1)
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.get_json()["plan"]["id"], plan_id)

        # Retrieve in list
        res_list = self.client.get("/api/crop-plans?season=Kharif", headers=self.headers1)
        self.assertEqual(res_list.status_code, 200)
        plans = res_list.get_json()["plans"]
        self.assertTrue(any(p["id"] == plan_id for p in plans))

    def test_update_crop_plan(self):
        """Update existing crop plan fields."""
        today = date.today()
        payload = {
            "crop_name": "Chickpea / हरभरा",
            "season": "Rabi",
            "planned_sowing_date": str(today + timedelta(days=30)),
            "expected_harvest_date": str(today + timedelta(days=120)),
            "land_area": 4.0
        }
        res_create = self.client.post("/api/crop-plans", headers=self.headers1, json=payload)
        plan_id = res_create.get_json()["plan"]["id"]

        update_payload = {
            "status": "In Progress",
            "land_area": 4.5,
            "notes": "Sowing commenced on scheduled date"
        }
        res_up = self.client.put(f"/api/crop-plans/{plan_id}", headers=self.headers1, json=update_payload)
        self.assertEqual(res_up.status_code, 200)
        updated = res_up.get_json()["plan"]
        self.assertEqual(updated["status"], "In Progress")
        self.assertEqual(updated["land_area"], 4.5)
        self.assertEqual(updated["notes"], "Sowing commenced on scheduled date")

    def test_delete_crop_plan(self):
        """Delete crop plan and verify 404 upon subsequent retrieval."""
        today = date.today()
        payload = {
            "crop_name": "Tomato",
            "season": "Zaid",
            "planned_sowing_date": str(today + timedelta(days=5)),
            "expected_harvest_date": str(today + timedelta(days=75)),
            "land_area": 2.0
        }
        res_create = self.client.post("/api/crop-plans", headers=self.headers1, json=payload)
        plan_id = res_create.get_json()["plan"]["id"]

        res_del = self.client.delete(f"/api/crop-plans/{plan_id}", headers=self.headers1)
        self.assertEqual(res_del.status_code, 200)

        res_get = self.client.get(f"/api/crop-plans/{plan_id}", headers=self.headers1)
        self.assertEqual(res_get.status_code, 404)

    def test_upcoming_crop_plans(self):
        """Upcoming endpoint returns active plans sorted by sowing date."""
        today = date.today()
        p1 = {
            "crop_name": "Wheat A",
            "season": "Rabi",
            "planned_sowing_date": str(today + timedelta(days=20)),
            "expected_harvest_date": str(today + timedelta(days=120)),
            "land_area": 3.0,
            "status": "Planned"
        }
        p2 = {
            "crop_name": "Wheat B",
            "season": "Rabi",
            "planned_sowing_date": str(today + timedelta(days=5)),
            "expected_harvest_date": str(today + timedelta(days=105)),
            "land_area": 2.0,
            "status": "Planned"
        }
        self.client.post("/api/crop-plans", headers=self.headers1, json=p1)
        self.client.post("/api/crop-plans", headers=self.headers1, json=p2)

        res = self.client.get("/api/crop-plans/upcoming?limit=5", headers=self.headers1)
        self.assertEqual(res.status_code, 200)
        upcoming = res.get_json()["upcoming_plans"]
        self.assertGreaterEqual(len(upcoming), 2)
        # Verify chronological order
        self.assertEqual(upcoming[0]["crop_name"], "Wheat B")
        self.assertEqual(upcoming[1]["crop_name"], "Wheat A")

    def test_summary_kpis(self):
        """Summary returns total plans, planned area and seasonal breakdown."""
        today = date.today()
        self.client.post("/api/crop-plans", headers=self.headers1, json={
            "crop_name": "Cotton",
            "season": "Kharif",
            "planned_sowing_date": str(today + timedelta(days=10)),
            "expected_harvest_date": str(today + timedelta(days=150)),
            "land_area": 6.0,
            "status": "Planned"
        })
        self.client.post("/api/crop-plans", headers=self.headers1, json={
            "crop_name": "Wheat",
            "season": "Rabi",
            "planned_sowing_date": str(today + timedelta(days=40)),
            "expected_harvest_date": str(today + timedelta(days=140)),
            "land_area": 4.0,
            "status": "In Progress"
        })

        res = self.client.get("/api/crop-plans/summary", headers=self.headers1)
        self.assertEqual(res.status_code, 200)
        s = res.get_json()["summary"]
        self.assertEqual(s["total_plans"], 2)
        self.assertEqual(s["planned_count"], 1)
        self.assertEqual(s["in_progress_count"], 1)
        self.assertEqual(s["total_planned_area"], 10.0)
        self.assertIn("Kharif", s["season_breakdown"])
        self.assertIn("Rabi", s["season_breakdown"])

    def test_multi_tenant_isolation(self):
        """Farmer B must not see, edit, or delete Farmer A's crop plans."""
        today = date.today()
        res_create = self.client.post("/api/crop-plans", headers=self.headers1, json={
            "crop_name": "Secret User1 Crop",
            "season": "Kharif",
            "planned_sowing_date": str(today + timedelta(days=15)),
            "expected_harvest_date": str(today + timedelta(days=100)),
            "land_area": 10.0
        })
        plan_id = res_create.get_json()["plan"]["id"]

        # User 2 tries to GET
        res_u2_get = self.client.get(f"/api/crop-plans/{plan_id}", headers=self.headers2)
        self.assertEqual(res_u2_get.status_code, 404)

        # User 2 tries to PUT
        res_u2_put = self.client.put(f"/api/crop-plans/{plan_id}", headers=self.headers2, json={"land_area": 15.0})
        self.assertEqual(res_u2_put.status_code, 404)

        # User 2 tries to DELETE
        res_u2_del = self.client.delete(f"/api/crop-plans/{plan_id}", headers=self.headers2)
        self.assertEqual(res_u2_del.status_code, 404)

        # User 2 listing contains 0 plans
        res_u2_list = self.client.get("/api/crop-plans", headers=self.headers2)
        self.assertEqual(res_u2_list.status_code, 200)
        self.assertEqual(len(res_u2_list.get_json()["plans"]), 0)


if __name__ == "__main__":
    unittest.main()
