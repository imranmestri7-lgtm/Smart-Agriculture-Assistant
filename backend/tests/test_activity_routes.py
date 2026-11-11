import os
import sys
import unittest
from datetime import date, datetime, timedelta

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from config import get_db_connection
from utils.auth_tokens import create_access_token


class TestActivityRoutes(unittest.TestCase):
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
        # Clean up activities created by test users
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM farm_activities WHERE user_id IN (%s, %s)", (self.user1_id, self.user2_id))
        cur.execute("DELETE FROM notifications WHERE user_id IN (%s, %s) AND unique_key LIKE 'act_%%'", (self.user1_id, self.user2_id))
        conn.commit()
        cur.close()
        conn.close()

    def tearDown(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM farm_activities WHERE user_id IN (%s, %s)", (self.user1_id, self.user2_id))
        cur.execute("DELETE FROM notifications WHERE user_id IN (%s, %s) AND unique_key LIKE 'act_%%'", (self.user1_id, self.user2_id))
        conn.commit()
        cur.close()
        conn.close()

    def test_activity_crud_success(self):
        """Test creating, reading, updating, and deleting a farm activity."""
        today_str = date.today().strftime("%Y-%m-%d")

        # 1. CREATE
        payload = {
            "title": "Soil Tilling and Land Prep",
            "category": "Land preparation",
            "scheduled_date": today_str,
            "scheduled_time": "08:30",
            "priority": "High",
            "status": "Pending",
            "description": "Deep plowing before Kharif sowing",
            "notes": "Use tractor with disk plow",
            "reminder_enabled": True
        }
        res = self.client.post("/api/activities", headers=self.headers1, json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        act_id = data["activity_id"]

        # 2. READ SINGLE
        res_get = self.client.get(f"/api/activities/{act_id}", headers=self.headers1)
        self.assertEqual(res_get.status_code, 200)
        act = res_get.get_json()["activity"]
        self.assertEqual(act["title"], "Soil Tilling and Land Prep")
        self.assertEqual(act["category"], "Land preparation")
        self.assertEqual(act["priority"], "High")
        self.assertEqual(act["status"], "Pending")
        self.assertEqual(act["scheduled_time"], "08:30")

        # 3. UPDATE (PUT)
        update_payload = {
            "title": "Soil Tilling and Harrowing",
            "category": "Land preparation",
            "scheduled_date": today_str,
            "scheduled_time": "09:00",
            "priority": "Medium",
            "status": "In Progress",
            "description": "Updated to include rotavator",
            "notes": "Completed first pass"
        }
        res_put = self.client.put(f"/api/activities/{act_id}", headers=self.headers1, json=update_payload)
        self.assertEqual(res_put.status_code, 200)

        res_check = self.client.get(f"/api/activities/{act_id}", headers=self.headers1)
        act_updated = res_check.get_json()["activity"]
        self.assertEqual(act_updated["title"], "Soil Tilling and Harrowing")
        self.assertEqual(act_updated["status"], "In Progress")
        self.assertEqual(act_updated["priority"], "Medium")

        # 4. DELETE
        res_del = self.client.delete(f"/api/activities/{act_id}", headers=self.headers1)
        self.assertEqual(res_del.status_code, 200)

        res_after = self.client.get(f"/api/activities/{act_id}", headers=self.headers1)
        self.assertEqual(res_after.status_code, 404)

    def test_activity_validation(self):
        """Test input validation for title, category, scheduled_date, and time."""
        # Missing title
        res = self.client.post("/api/activities", headers=self.headers1, json={
            "category": "Irrigation",
            "scheduled_date": "2026-11-15"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("title is required", res.get_json()["message"].lower())

        # Invalid category
        res = self.client.post("/api/activities", headers=self.headers1, json={
            "title": "Test task",
            "category": "InvalidNonExistentCategory",
            "scheduled_date": "2026-11-15"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("invalid category", res.get_json()["message"].lower())

        # Invalid date format
        res = self.client.post("/api/activities", headers=self.headers1, json={
            "title": "Test task",
            "category": "Irrigation",
            "scheduled_date": "15-11-2026"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("date format", res.get_json()["message"].lower())

        # Invalid time format
        res = self.client.post("/api/activities", headers=self.headers1, json={
            "title": "Test task",
            "category": "Irrigation",
            "scheduled_date": "2026-11-15",
            "scheduled_time": "99:99"
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("time format", res.get_json()["message"].lower())

    def test_activity_status_patch(self):
        """Test patching activity status to Completed sets completion_date."""
        today_str = date.today().strftime("%Y-%m-%d")
        res = self.client.post("/api/activities", headers=self.headers1, json={
            "title": "Irrigate South Field",
            "category": "Irrigation",
            "scheduled_date": today_str,
            "status": "Pending"
        })
        act_id = res.get_json()["activity_id"]

        # Mark as Completed
        res_patch = self.client.patch(f"/api/activities/{act_id}/status", headers=self.headers1, json={
            "status": "Completed"
        })
        self.assertEqual(res_patch.status_code, 200)
        data = res_patch.get_json()
        self.assertEqual(data["status_value"], "Completed")
        self.assertEqual(data["completion_date"], today_str)

        # Verify DB
        res_get = self.client.get(f"/api/activities/{act_id}", headers=self.headers1)
        self.assertEqual(res_get.get_json()["activity"]["status"], "Completed")
        self.assertEqual(res_get.get_json()["activity"]["completion_date"], today_str)

    def test_activity_postpone_patch(self):
        """Test postponing an activity updates scheduled date and notes."""
        today = date.today()
        res = self.client.post("/api/activities", headers=self.headers1, json={
            "title": "Foliar Spray Application",
            "category": "Fertilizer application",
            "scheduled_date": today.strftime("%Y-%m-%d"),
            "status": "Pending"
        })
        act_id = res.get_json()["activity_id"]

        new_date = (today + timedelta(days=3)).strftime("%Y-%m-%d")
        res_postpone = self.client.patch(f"/api/activities/{act_id}/postpone", headers=self.headers1, json={
            "scheduled_date": new_date,
            "notes": "Postponed due to unexpected rain forecast"
        })
        self.assertEqual(res_postpone.status_code, 200)

        res_get = self.client.get(f"/api/activities/{act_id}", headers=self.headers1)
        act = res_get.get_json()["activity"]
        self.assertEqual(act["scheduled_date"], new_date)
        self.assertEqual(act["status"], "Postponed")
        self.assertIn("unexpected rain", act["notes"])

    def test_activity_calendar_endpoint(self):
        """Test monthly calendar endpoint grouping and indicators."""
        today = date.today()
        # Create activities on today and today + 2
        self.client.post("/api/activities", headers=self.headers1, json={
            "title": "Weed Removal",
            "category": "Weed management",
            "scheduled_date": today.strftime("%Y-%m-%d"),
            "priority": "High"
        })
        other_date = (today + timedelta(days=2))
        if other_date.month == today.month:
            self.client.post("/api/activities", headers=self.headers1, json={
                "title": "Crop Inspection",
                "category": "Crop inspection",
                "scheduled_date": other_date.strftime("%Y-%m-%d"),
                "priority": "Low"
            })

        res_cal = self.client.get(f"/api/activities/calendar?year={today.year}&month={today.month}", headers=self.headers1)
        self.assertEqual(res_cal.status_code, 200)
        cal_data = res_cal.get_json()
        self.assertEqual(cal_data["year"], today.year)
        self.assertEqual(cal_data["month"], today.month)
        self.assertGreaterEqual(cal_data["total_activities"], 1)

        # Verify today's day entry
        today_entry = next((d for d in cal_data["days"] if d["is_today"]), None)
        self.assertIsNotNone(today_entry)
        self.assertGreaterEqual(today_entry["activity_count"], 1)
        self.assertTrue(today_entry["has_high_priority"])

    def test_activity_summary_endpoint(self):
        """Test summary endpoint returns accurate counters for today, upcoming, overdue, and completed."""
        today = date.today()
        past_date = (today - timedelta(days=2)).strftime("%Y-%m-%d")
        future_date = (today + timedelta(days=3)).strftime("%Y-%m-%d")

        # Overdue task
        self.client.post("/api/activities", headers=self.headers1, json={
            "title": "Old Task",
            "category": "Irrigation",
            "scheduled_date": past_date,
            "status": "Pending"
        })
        # Today task
        self.client.post("/api/activities", headers=self.headers1, json={
            "title": "Today Task",
            "category": "Harvesting",
            "scheduled_date": today.strftime("%Y-%m-%d"),
            "status": "Pending"
        })
        # Upcoming task
        self.client.post("/api/activities", headers=self.headers1, json={
            "title": "Upcoming Task",
            "category": "Disease monitoring",
            "scheduled_date": future_date,
            "status": "Pending"
        })
        # Completed task
        self.client.post("/api/activities", headers=self.headers1, json={
            "title": "Done Task",
            "category": "Land preparation",
            "scheduled_date": past_date,
            "status": "Completed"
        })

        res = self.client.get("/api/activities/summary", headers=self.headers1)
        self.assertEqual(res.status_code, 200)
        summary = res.get_json()["summary"]
        self.assertGreaterEqual(summary["today_count"], 1)
        self.assertGreaterEqual(summary["upcoming_count"], 1)
        self.assertGreaterEqual(summary["overdue_count"], 1)
        self.assertGreaterEqual(summary["completed_count"], 1)
        self.assertGreaterEqual(summary["pending_count"], 3)
        self.assertGreaterEqual(summary["total_count"], 4)

    def test_activity_suggestions_crop_aware(self):
        """Test intelligent suggestions derived from registered farm crops and growth stages."""
        res = self.client.get("/api/activities/suggestions", headers=self.headers1)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIsInstance(data["suggestions"], list)
        if data["suggestions"]:
            sug = data["suggestions"][0]
            self.assertIn("title", sug)
            self.assertIn("category", sug)
            self.assertIn("reason", sug)
            self.assertIn("priority", sug)

    def test_activity_data_isolation(self):
        """Ensure User 2 cannot access, update, or delete User 1's activities."""
        today_str = date.today().strftime("%Y-%m-%d")
        res1 = self.client.post("/api/activities", headers=self.headers1, json={
            "title": "User 1 Secret Task",
            "category": "Crop inspection",
            "scheduled_date": today_str
        })
        act_id1 = res1.get_json()["activity_id"]

        # User 2 tries to GET
        res_u2_get = self.client.get(f"/api/activities/{act_id1}", headers=self.headers2)
        self.assertEqual(res_u2_get.status_code, 404)

        # User 2 tries to PUT
        res_u2_put = self.client.put(f"/api/activities/{act_id1}", headers=self.headers2, json={
            "title": "Hacked Title",
            "category": "Crop inspection",
            "scheduled_date": today_str
        })
        self.assertEqual(res_u2_put.status_code, 404)

        # User 2 tries to DELETE
        res_u2_del = self.client.delete(f"/api/activities/{act_id1}", headers=self.headers2)
        self.assertEqual(res_u2_del.status_code, 404)

        # Verify activity still belongs intact to User 1
        res_verify = self.client.get(f"/api/activities/{act_id1}", headers=self.headers1)
        self.assertEqual(res_verify.status_code, 200)
        self.assertEqual(res_verify.get_json()["activity"]["title"], "User 1 Secret Task")

    def test_activity_filtering(self):
        """Test filtering activities by category and status."""
        today_str = date.today().strftime("%Y-%m-%d")
        self.client.post("/api/activities", headers=self.headers1, json={
            "title": "Irrigation Task",
            "category": "Irrigation",
            "scheduled_date": today_str,
            "status": "Pending"
        })
        self.client.post("/api/activities", headers=self.headers1, json={
            "title": "Weed Task",
            "category": "Weed management",
            "scheduled_date": today_str,
            "status": "Completed"
        })

        # Filter by category
        res_cat = self.client.get("/api/activities?category=irrigation", headers=self.headers1)
        self.assertEqual(res_cat.status_code, 200)
        acts = res_cat.get_json()["activities"]
        self.assertTrue(all(a["category"] == "Irrigation" for a in acts))

        # Filter by status
        res_st = self.client.get("/api/activities?status=completed", headers=self.headers1)
        self.assertEqual(res_st.status_code, 200)
        acts_st = res_st.get_json()["activities"]
        self.assertTrue(all(a["status"] == "Completed" for a in acts_st))

    def test_activity_notification_integration(self):
        """Test that scheduled activities trigger notifications when due or overdue."""
        today_str = date.today().strftime("%Y-%m-%d")
        self.client.post("/api/activities", headers=self.headers1, json={
            "title": "Urgent Spray Task",
            "category": "Pesticide application",
            "scheduled_date": today_str,
            "priority": "High",
            "status": "Pending",
            "reminder_enabled": True
        })

        # Calling summary triggers sync_activity_notifications_for_user
        res_summary = self.client.get("/api/activities/summary", headers=self.headers1)
        self.assertEqual(res_summary.status_code, 200)

        # Check notifications table
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM notifications WHERE user_id = %s AND unique_key LIKE 'act_today_%%'", (self.user1_id,))
        notifs = cur.fetchall()
        cur.close()
        conn.close()

        self.assertGreaterEqual(len(notifs), 1)
        self.assertIn("Urgent Spray Task", notifs[0]["title"])


if __name__ == "__main__":
    unittest.main()
