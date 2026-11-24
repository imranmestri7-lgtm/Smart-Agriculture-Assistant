"""
AgriSmart - Feature Upgrade 9, Phase 3 (Part 1): Crop Calendar Foundation Unit Tests
Tests backend crop calendar API:
- Monthly & weekly calendar data generation
- Sowing dates, harvest dates, and growing spans
- Multi-factor filters (farm, season, crop, status)
- Multi-tenant data isolation (user_id isolation)
- Month boundaries and error/edge cases
"""

import unittest
from datetime import date, timedelta
from flask import Flask

from routes.crop_plan_routes import crop_plan_bp
from utils.auth_tokens import create_access_token
from config import get_db_connection


class TestCropCalendarAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config["TESTING"] = True
        cls.app.register_blueprint(crop_plan_bp)
        cls.client = cls.app.test_client()

        cls.user_id = 1
        cls.other_user_id = 2
        cls.token = create_access_token(cls.user_id)
        cls.other_token = create_access_token(cls.other_user_id)
        cls.headers = {"Authorization": f"Bearer {cls.token}"}
        cls.other_headers = {"Authorization": f"Bearer {cls.other_token}"}

        # Set up test data in MySQL
        cls._setup_test_plans()

    @classmethod
    def tearDownClass(cls):
        cls._cleanup_test_plans()

    @classmethod
    def _setup_test_plans(cls):
        conn = get_db_connection()
        cur = conn.cursor()

        # Clean prior test plans for test users
        cur.execute("DELETE FROM crop_plans WHERE user_id IN (%s, %s)", (cls.user_id, cls.other_user_id))

        # Plan 1 for User 1: Kharif Soybean (Sowing: 2026-06-20, Harvest: 2026-10-05)
        cur.execute("""
            INSERT INTO crop_plans (
                user_id, farm_id, crop_name, variety, season, planning_year,
                planned_sowing_date, expected_harvest_date, land_area, area_unit,
                status, notes
            ) VALUES (
                %s, 2, 'Soybean', 'JS-335', 'Kharif', 2026,
                '2026-06-20', '2026-10-05', 5.0, 'Acres',
                'Completed', '__CAL_TEST__ Plan 1 User 1'
            )
        """, (cls.user_id,))

        # Plan 2 for User 1: Rabi Wheat (Sowing: 2026-11-10, Harvest: 2027-03-05)
        cur.execute("""
            INSERT INTO crop_plans (
                user_id, farm_id, crop_name, variety, season, planning_year,
                planned_sowing_date, expected_harvest_date, land_area, area_unit,
                status, notes
            ) VALUES (
                %s, 2, 'Wheat', 'Lokwan', 'Rabi', 2026,
                '2026-11-10', '2027-03-05', 8.0, 'Acres',
                'Planned', '__CAL_TEST__ Plan 2 User 1'
            )
        """, (cls.user_id,))

        # Plan 3 for User 1: Rabi Chickpea on Farm 3 (Sowing: 2026-11-20, Harvest: 2027-02-25)
        cur.execute("""
            INSERT INTO crop_plans (
                user_id, farm_id, crop_name, variety, season, planning_year,
                planned_sowing_date, expected_harvest_date, land_area, area_unit,
                status, notes
            ) VALUES (
                %s, 3, 'Chickpea', 'Vijay', 'Rabi', 2026,
                '2026-11-20', '2027-02-25', 4.0, 'Acres',
                'In Progress', '__CAL_TEST__ Plan 3 User 1'
            )
        """, (cls.user_id,))

        # Plan 4 for User 2 (isolated): Zaid Watermelon (Sowing: 2026-11-15, Harvest: 2027-02-15)
        cur.execute("""
            INSERT INTO crop_plans (
                user_id, farm_id, crop_name, variety, season, planning_year,
                planned_sowing_date, expected_harvest_date, land_area, area_unit,
                status, notes
            ) VALUES (
                %s, NULL, 'Watermelon', 'Sugar Baby', 'Zaid', 2026,
                '2026-11-15', '2027-02-15', 2.0, 'Acres',
                'Planned', '__CAL_TEST__ Plan 4 User 2 Secret'
            )
        """, (cls.other_user_id,))

        conn.commit()
        cur.close()
        conn.close()

    @classmethod
    def _cleanup_test_plans(cls):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM crop_plans WHERE user_id IN (%s, %s)", (cls.user_id, cls.other_user_id))
        conn.commit()
        cur.close()
        conn.close()

    def test_01_calendar_unauthenticated(self):
        """Calendar API requires valid JWT Bearer authentication."""
        res = self.client.get("/api/crop-plans/calendar")
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data["status"], "error")

    def test_02_calendar_month_view(self):
        """Month view returns month metadata, 30 days for November 2026, and active events."""
        res = self.client.get(
            "/api/crop-plans/calendar?year=2026&month=11&view=month",
            headers=self.headers
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["year"], 2026)
        self.assertEqual(data["month"], 11)
        self.assertEqual(data["month_name"], "November")
        self.assertEqual(len(data["days"]), 30)

        # Check November 10 (Wheat sowing date)
        day_10 = next((d for d in data["days"] if d["date"] == "2026-11-10"), None)
        self.assertIsNotNone(day_10)
        self.assertTrue(any(e["crop_name"] == "Wheat" and e["event_type"] == "sowing" for e in day_10["sowing_events"]))

        # Check November 20 (Chickpea sowing date)
        day_20 = next((d for d in data["days"] if d["date"] == "2026-11-20"), None)
        self.assertIsNotNone(day_20)
        self.assertTrue(any(e["crop_name"] == "Chickpea" and e["event_type"] == "sowing" for e in day_20["sowing_events"]))

        # Check November 25: Wheat is growing
        day_25 = next((d for d in data["days"] if d["date"] == "2026-11-25"), None)
        self.assertIsNotNone(day_25)
        self.assertTrue(any(g["crop_name"] == "Wheat" and g["event_type"] == "growing" for g in day_25["growing_crops"]))

    def test_03_calendar_week_view(self):
        """Week view returns exactly 7 days starting on Monday and ending on Sunday."""
        res = self.client.get(
            "/api/crop-plans/calendar?view=week&date=2026-11-11",
            headers=self.headers
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["view"], "week")
        self.assertEqual(len(data["days"]), 7)
        # Week containing 2026-11-11 (Wed) starts on 2026-11-09 (Mon) and ends on 2026-11-15 (Sun)
        self.assertEqual(data["days"][0]["date"], "2026-11-09")
        self.assertEqual(data["days"][0]["weekday"], 0)  # Monday
        self.assertEqual(data["days"][-1]["date"], "2026-11-15")
        self.assertEqual(data["days"][-1]["weekday"], 6)  # Sunday

        # November 10 (Tuesday) has Wheat sowing event
        tue_day = data["days"][1]
        self.assertEqual(tue_day["date"], "2026-11-10")
        self.assertEqual(len(tue_day["sowing_events"]), 1)
        self.assertEqual(tue_day["sowing_events"][0]["crop_name"], "Wheat")

    def test_04_calendar_custom_date_range(self):
        """Calendar supports custom start_date and end_date filtering."""
        res = self.client.get(
            "/api/crop-plans/calendar?start_date=2026-11-01&end_date=2026-11-15",
            headers=self.headers
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(len(data["days"]), 15)
        self.assertEqual(data["start_date"], "2026-11-01")
        self.assertEqual(data["end_date"], "2026-11-15")

    def test_05_calendar_farm_filter(self):
        """Filter by farm_id restricts events to that specific farm."""
        # Farm 3 only has Chickpea
        res = self.client.get(
            "/api/crop-plans/calendar?year=2026&month=11&farm_id=3",
            headers=self.headers
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(all(p["farm_id"] == 3 for p in data["plans"]))
        crop_names = [p["crop_name"] for p in data["plans"]]
        self.assertIn("Chickpea", crop_names)
        self.assertNotIn("Wheat", crop_names)

    def test_06_calendar_season_filter(self):
        """Filter by season restricts calendar to plans of that season."""
        res = self.client.get(
            "/api/crop-plans/calendar?year=2026&month=11&season=Rabi",
            headers=self.headers
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(all(p["season"] == "Rabi" for p in data["plans"]))

    def test_07_calendar_crop_filter(self):
        """Filter by crop keyword restricts calendar results."""
        res = self.client.get(
            "/api/crop-plans/calendar?year=2026&month=11&crop=Wheat",
            headers=self.headers
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(len(data["plans"]), 1)
        self.assertEqual(data["plans"][0]["crop_name"], "Wheat")

    def test_08_calendar_status_filter(self):
        """Filter by status restricts calendar results."""
        res = self.client.get(
            "/api/crop-plans/calendar?year=2026&month=11&status=Planned",
            headers=self.headers
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(all(p["status"] == "Planned" for p in data["plans"]))

    def test_09_farmer_data_isolation(self):
        """User 1 cannot see User 2's crop plans on the calendar, and vice versa."""
        # User 1 query for November 2026
        res1 = self.client.get(
            "/api/crop-plans/calendar?year=2026&month=11",
            headers=self.headers
        )
        data1 = res1.get_json()
        self.assertFalse(any("Watermelon" in p["crop_name"] for p in data1["plans"]))

        # User 2 query for November 2026
        res2 = self.client.get(
            "/api/crop-plans/calendar?year=2026&month=11",
            headers=self.other_headers
        )
        data2 = res2.get_json()
        self.assertTrue(any("Watermelon" in p["crop_name"] for p in data2["plans"]))
        self.assertFalse(any("Wheat" in p["crop_name"] for p in data2["plans"]))
        self.assertFalse(any("Chickpea" in p["crop_name"] for p in data2["plans"]))

    def test_10_invalid_dates_handling(self):
        """Invalid date ranges or formats return 400 or default safely."""
        # start_date > end_date
        res = self.client.get(
            "/api/crop-plans/calendar?start_date=2026-11-20&end_date=2026-11-10",
            headers=self.headers
        )
        self.assertEqual(res.status_code, 400)

        # malformed date
        res = self.client.get(
            "/api/crop-plans/calendar?start_date=bad-date&end_date=2026-11-10",
            headers=self.headers
        )
        self.assertEqual(res.status_code, 400)

        # month out of bounds defaults to current month
        res = self.client.get(
            "/api/crop-plans/calendar?month=99",
            headers=self.headers
        )
        self.assertEqual(res.status_code, 200)

    def test_11_month_boundary_transition(self):
        """Range spanning across month boundaries (e.g. Nov 28 to Dec 5) works seamlessly."""
        res = self.client.get(
            "/api/crop-plans/calendar?start_date=2026-11-28&end_date=2026-12-05",
            headers=self.headers
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(len(data["days"]), 8)
        self.assertEqual(data["days"][0]["date"], "2026-11-28")
        self.assertEqual(data["days"][-1]["date"], "2026-12-05")


if __name__ == "__main__":
    unittest.main()
