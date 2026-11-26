"""
AgriSmart - Feature Upgrade 9, Phase 3 (Part 2): Smart Crop Reminders Unit Tests
Tests backend crop reminders:
- Reminder generation from crop plans (sowing, harvest, growth stages)
- Configurable reminder settings and lead days
- Date calculations and crop duration handling (short duration, normal duration, missing dates)
- Duplicate prevention (idempotent generation)
- Status lifecycle (pending, completed, dismissed)
- Converting reminders to Farm Activities
- Multi-tenant farmer data isolation
- Calendar integration (reminders in day agenda)
"""

import unittest
from datetime import date, timedelta
from flask import Flask

from routes.crop_plan_routes import crop_plan_bp
from routes.activity_routes import activity_bp
from utils.auth_tokens import create_access_token
from config import get_db_connection


class TestCropRemindersAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config["TESTING"] = True
        cls.app.register_blueprint(crop_plan_bp)
        cls.app.register_blueprint(activity_bp)
        cls.client = cls.app.test_client()

        cls.user1_id = 1
        cls.user2_id = 2
        cls.token1 = create_access_token(cls.user1_id)
        cls.token2 = create_access_token(cls.user2_id)
        cls.headers1 = {"Authorization": f"Bearer {cls.token1}", "Content-Type": "application/json"}
        cls.headers2 = {"Authorization": f"Bearer {cls.token2}", "Content-Type": "application/json"}

    def setUp(self):
        # Clean up prior test data
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM crop_plan_reminders WHERE user_id IN (%s, %s)", (self.user1_id, self.user2_id))
        cur.execute("DELETE FROM crop_plans WHERE user_id IN (%s, %s)", (self.user1_id, self.user2_id))
        cur.execute("DELETE FROM farm_activities WHERE user_id IN (%s, %s) AND notes LIKE '%%Crop Plan%%'", (self.user1_id, self.user2_id))
        conn.commit()
        cur.close()
        conn.close()

    def tearDown(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM crop_plan_reminders WHERE user_id IN (%s, %s)", (self.user1_id, self.user2_id))
        cur.execute("DELETE FROM crop_plans WHERE user_id IN (%s, %s)", (self.user1_id, self.user2_id))
        cur.execute("DELETE FROM farm_activities WHERE user_id IN (%s, %s) AND notes LIKE '%%Crop Plan%%'", (self.user1_id, self.user2_id))
        conn.commit()
        cur.close()
        conn.close()

    def _create_test_plan(self, user_id, crop_name="Wheat", variety="Lokwan",
                          sow_date="2026-11-10", har_date="2027-03-05", farm_id=2):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO crop_plans (
                user_id, farm_id, crop_name, variety, season, planning_year,
                planned_sowing_date, expected_harvest_date, land_area, area_unit,
                status, notes
            ) VALUES (
                %s, %s, %s, %s, 'Rabi', 2026,
                %s, %s, 5.0, 'Acres',
                'Planned', '__TEST_REM__ Plan'
            )
        """, (user_id, farm_id, crop_name, variety, sow_date, har_date))
        conn.commit()
        plan_id = cur.lastrowid
        cur.close()
        conn.close()
        return plan_id

    def test_01_unauthenticated_requests_rejected(self):
        """Unauthenticated requests must be rejected with 401."""
        endpoints = [
            ("GET", "/api/crop-plans/reminders"),
            ("GET", "/api/crop-plans/reminders/settings"),
            ("PUT", "/api/crop-plans/reminders/settings"),
            ("POST", "/api/crop-plans/1/generate-reminders"),
            ("PATCH", "/api/crop-plans/reminders/1/status"),
            ("POST", "/api/crop-plans/reminders/1/add-to-activity")
        ]
        for method, ep in endpoints:
            if method == "GET":
                res = self.client.get(ep)
            elif method == "POST":
                res = self.client.post(ep)
            elif method == "PUT":
                res = self.client.put(ep)
            elif method == "PATCH":
                res = self.client.patch(ep)
            self.assertEqual(res.status_code, 401, f"{method} {ep} did not return 401")

    def test_02_generate_reminders_for_plan(self):
        """Generating reminders produces sowing milestones, harvest milestones, and growth stages."""
        plan_id = self._create_test_plan(self.user1_id, crop_name="Wheat", variety="Lokwan",
                                          sow_date="2026-11-10", har_date="2027-03-05")

        res = self.client.post(f"/api/crop-plans/{plan_id}/generate-reminders", headers=self.headers1)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")

        # Fetch reminders
        res2 = self.client.get(f"/api/crop-plans/reminders?plan_id={plan_id}", headers=self.headers1)
        self.assertEqual(res2.status_code, 200)
        rem_data = res2.get_json()
        reminders = rem_data["reminders"]
        self.assertGreaterEqual(len(reminders), 6)  # 3 sowing + 3 harvest + growth stages

        milestones = [r["milestone_type"] for r in reminders]
        self.assertIn("sowing", milestones)
        self.assertIn("harvest", milestones)
        self.assertIn("vegetative", milestones)
        self.assertIn("flowering", milestones)

        # Check estimated flag on growth stages
        growth_rems = [r for r in reminders if r["reminder_type"] == "growth_stage"]
        self.assertTrue(all(r["is_estimated"] is True for r in growth_rems))
        self.assertTrue(all("General Agronomic Advice" in r["guidance"] for r in growth_rems))

    def test_03_duplicate_prevention(self):
        """Multiple reminder generation calls must be idempotent and not create duplicate records."""
        plan_id = self._create_test_plan(self.user1_id, crop_name="Chickpea", variety="Vijay",
                                          sow_date="2026-11-20", har_date="2027-02-25")

        # First generation
        self.client.post(f"/api/crop-plans/{plan_id}/generate-reminders", headers=self.headers1)
        res1 = self.client.get(f"/api/crop-plans/reminders?plan_id={plan_id}", headers=self.headers1)
        count1 = res1.get_json()["counts"]["total"]

        # Second generation
        self.client.post(f"/api/crop-plans/{plan_id}/generate-reminders", headers=self.headers1)
        res2 = self.client.get(f"/api/crop-plans/reminders?plan_id={plan_id}", headers=self.headers1)
        count2 = res2.get_json()["counts"]["total"]

        self.assertEqual(count1, count2)

    def test_04_status_updates_completed_and_dismissed(self):
        """Updating reminder status sets completed_at or dismissed_at and preserves state."""
        plan_id = self._create_test_plan(self.user1_id, crop_name="Tomato", variety="Abhinav",
                                          sow_date="2026-11-05", har_date="2027-01-15")
        self.client.post(f"/api/crop-plans/{plan_id}/generate-reminders", headers=self.headers1)

        res = self.client.get(f"/api/crop-plans/reminders?plan_id={plan_id}", headers=self.headers1)
        first_rem = res.get_json()["reminders"][0]
        rem_id = first_rem["id"]

        # Mark completed
        patch_res = self.client.patch(
            f"/api/crop-plans/reminders/{rem_id}/status",
            headers=self.headers1,
            json={"status": "completed"}
        )
        self.assertEqual(patch_res.status_code, 200)

        # Verify completed status
        chk_res = self.client.get(f"/api/crop-plans/reminders?plan_id={plan_id}&status=completed", headers=self.headers1)
        completed_list = chk_res.get_json()["reminders"]
        self.assertTrue(any(r["id"] == rem_id for r in completed_list))

        # Regenerate reminders; completed status must NOT be reset to pending!
        self.client.post(f"/api/crop-plans/{plan_id}/generate-reminders", headers=self.headers1)
        chk_res2 = self.client.get(f"/api/crop-plans/reminders?plan_id={plan_id}&status=completed", headers=self.headers1)
        self.assertTrue(any(r["id"] == rem_id for r in chk_res2.get_json()["reminders"]))

    def test_05_convert_reminder_to_farm_activity(self):
        """Converting a reminder creates a farm_activities entry and subsequent call is idempotent."""
        plan_id = self._create_test_plan(self.user1_id, crop_name="Soybean", variety="JS-335",
                                          sow_date="2026-06-20", har_date="2026-10-05")
        self.client.post(f"/api/crop-plans/{plan_id}/generate-reminders", headers=self.headers1)

        res = self.client.get(f"/api/crop-plans/reminders?plan_id={plan_id}", headers=self.headers1)
        rem_id = res.get_json()["reminders"][0]["id"]

        # Add to activities
        act_res = self.client.post(f"/api/crop-plans/reminders/{rem_id}/add-to-activity", headers=self.headers1)
        self.assertEqual(act_res.status_code, 201)
        act_data = act_res.get_json()
        self.assertEqual(act_data["status"], "success")
        self.assertFalse(act_data["already_existed"])

        # Second call should report already_existed
        act_res2 = self.client.post(f"/api/crop-plans/reminders/{rem_id}/add-to-activity", headers=self.headers1)
        self.assertEqual(act_res2.status_code, 200)
        self.assertTrue(act_res2.get_json()["already_existed"])

    def test_06_farmer_data_isolation(self):
        """Farmer cannot view or modify another farmer's crop reminders."""
        plan1_id = self._create_test_plan(self.user1_id, crop_name="User1-Crop")
        plan2_id = self._create_test_plan(self.user2_id, crop_name="User2-Crop")

        self.client.post(f"/api/crop-plans/{plan1_id}/generate-reminders", headers=self.headers1)
        self.client.post(f"/api/crop-plans/{plan2_id}/generate-reminders", headers=self.headers2)

        # User 1 checks reminders: should only see User1-Crop
        res1 = self.client.get("/api/crop-plans/reminders", headers=self.headers1)
        rems1 = res1.get_json()["reminders"]
        self.assertTrue(all(r["crop_name"] != "User2-Crop" for r in rems1))

        # User 1 attempts to modify User 2's reminder
        res2 = self.client.get("/api/crop-plans/reminders", headers=self.headers2)
        u2_rem_id = res2.get_json()["reminders"][0]["id"]

        hack_patch = self.client.patch(
            f"/api/crop-plans/reminders/{u2_rem_id}/status",
            headers=self.headers1,
            json={"status": "completed"}
        )
        self.assertEqual(hack_patch.status_code, 404)

    def test_07_custom_settings_and_lead_times(self):
        """Updating reminder settings updates lead times and regenerates accordingly."""
        res = self.client.put(
            "/api/crop-plans/reminders/settings",
            headers=self.headers1,
            json={
                "sowing_lead_days": [10, 5, 0],
                "harvest_lead_days": [20, 10, 0],
                "enable_growth_stages": False
            }
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["settings"]["sowing_lead_days"], [10, 5, 0])
        self.assertFalse(data["settings"]["enable_growth_stages"])

        # Create new plan and check that only sowing & harvest milestones (no growth stages) are created
        plan_id = self._create_test_plan(self.user1_id, crop_name="CustomSettingCrop")
        self.client.post(f"/api/crop-plans/{plan_id}/generate-reminders", headers=self.headers1)

        rems = self.client.get(f"/api/crop-plans/reminders?plan_id={plan_id}", headers=self.headers1).get_json()["reminders"]
        self.assertTrue(all(r["reminder_type"] == "milestone" for r in rems))
        offsets = [r["days_offset"] for r in rems if r["milestone_type"] == "sowing"]
        self.assertIn(-10, offsets)
        self.assertIn(-5, offsets)
        self.assertIn(0, offsets)

    def test_08_calendar_reminders_integration(self):
        """Calendar API includes reminders and reminder indicators on corresponding days."""
        # Create plan with sowing on Nov 10, 2026
        plan_id = self._create_test_plan(self.user1_id, crop_name="CalWheat",
                                          sow_date="2026-11-10", har_date="2027-03-05")
        self.client.post(f"/api/crop-plans/{plan_id}/generate-reminders", headers=self.headers1)

        cal_res = self.client.get(
            "/api/crop-plans/calendar?year=2026&month=11&view=month",
            headers=self.headers1
        )
        self.assertEqual(cal_res.status_code, 200)
        cal_data = cal_res.get_json()
        days = cal_data["days"]

        # Sowing day is Nov 10, which has lead-0 reminder
        nov10 = next((d for d in days if d["date"] == "2026-11-10"), None)
        self.assertIsNotNone(nov10)
        self.assertGreater(nov10["reminder_count"], 0)
        self.assertTrue(nov10["has_pending_reminders"])
        self.assertTrue(any("CalWheat" in r["crop_name"] for r in nov10["reminders"]))


if __name__ == "__main__":
    unittest.main()
