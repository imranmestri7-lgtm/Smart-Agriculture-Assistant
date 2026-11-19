"""
Unit tests for Crop Rotation Analysis (Feature Upgrade 9, Phase 2 Part 1)
Tests:
- Botanical classification (Fabaceae, Poaceae, Solanaceae, Malvaceae, etc.)
- Monoculture / Repeated crop detection
- Unsuitable consecutive family detection (Solanaceae, Malvaceae, Poaceae)
- Legume rotation benefits and recommendations
- Insufficient history detection (< 2 records)
- API endpoint GET /api/crop-plans/rotation-analysis authentication & response
- Multi-tenant farmer data isolation
"""

import os
import sys
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from config import get_db_connection
from utils.auth_tokens import create_access_token
from utils.crop_rotation_engine import (
    classify_crop,
    analyze_crop_rotation_for_farm,
    analyze_all_farmer_farms,
    BOTANICAL_FAMILIES
)


class TestCropRotationUnit(unittest.TestCase):
    """Test botanical classification and algorithmic agronomic rotation analysis."""

    def test_botanical_classification_known_crops(self):
        """Test classifying crops across different botanical families including Hindi/Marathi names."""
        legumes = ["Chickpea", "Chana", "Soybean", "Soyabean", "Moong", "Green Gram", "Tur", "Pigeon Pea", "Groundnut", "Urad"]
        for c in legumes:
            info = classify_crop(c)
            self.assertEqual(info["family"], "Fabaceae", f"Failed for {c}")
            self.assertEqual(info["category"], "legume")
            self.assertTrue(info["nitrogen_fixer"])
            self.assertTrue(info["is_legume"])

        cereals = ["Wheat", "Gehun", "Rice", "Paddy", "Maize", "Corn", "Sugarcane", "Jowar", "Bajra"]
        for c in cereals:
            info = classify_crop(c)
            self.assertEqual(info["family"], "Poaceae", f"Failed for {c}")
            self.assertEqual(info["category"], "cereal")
            self.assertFalse(info["nitrogen_fixer"])
            self.assertFalse(info["is_legume"])

        solanaceous = ["Tomato", "Tamatar", "Potato", "Batata", "Brinjal", "Eggplant", "Chilli", "Mirchi", "Capsicum"]
        for c in solanaceous:
            info = classify_crop(c)
            self.assertEqual(info["family"], "Solanaceae", f"Failed for {c}")
            self.assertEqual(info["category"], "solanaceous")

        malvaceae = ["Cotton", "Kapas", "Okra", "Bhindi"]
        for c in malvaceae:
            info = classify_crop(c)
            self.assertEqual(info["family"], "Malvaceae", f"Failed for {c}")

    def test_classify_unknown_crop(self):
        """Test fallback for unknown or exotic crops."""
        info = classify_crop("Dragon Fruit Exotic 123")
        self.assertEqual(info["family"], "Other")
        self.assertEqual(info["category"], "other")
        self.assertFalse(info["nitrogen_fixer"])
        self.assertFalse(info["is_legume"])

    def test_insufficient_history(self):
        """Fewer than 2 crop records must report insufficient history."""
        farm_info = {"id": 1, "farm_name": "Test Farm", "location": "Pune"}
        
        # 0 records
        res0 = analyze_crop_rotation_for_farm(farm_info, [], [])
        self.assertFalse(res0["has_sufficient_history"])
        self.assertIsNone(res0["rotation_score"])
        self.assertEqual(res0["crop_count"], 0)
        self.assertIn("insufficient", res0["insufficient_reason"].lower())

        # 1 record
        res1 = analyze_crop_rotation_for_farm(farm_info, [{"crop_name": "Wheat", "planting_date": "2025-11-01"}], [])
        self.assertFalse(res1["has_sufficient_history"])
        self.assertEqual(res1["crop_count"], 1)

    def test_monoculture_repeated_crop_detection(self):
        """Identical crop repeated consecutively must trigger high risk warning."""
        farm_info = {"id": 1, "farm_name": "Plot A", "location": "Nashik"}
        history = [
            {"crop_name": "Cotton", "planting_date": "2024-06-15", "growth_status": "Harvested"}
        ]
        plans = [
            {"crop_name": "Cotton", "planned_sowing_date": "2025-06-15", "season": "Kharif", "status": "Planned"}
        ]

        res = analyze_crop_rotation_for_farm(farm_info, history, plans)
        self.assertTrue(res["has_sufficient_history"])
        self.assertGreater(len(res["issues"]), 0)
        
        # Check that monoculture was caught
        monoculture_issues = [i for i in res["issues"] if i["type"] == "REPEATED_CROP"]
        self.assertEqual(len(monoculture_issues), 1)
        self.assertIn(monoculture_issues[0]["severity"], ["CRITICAL", "HIGH"])
        self.assertIn("Cotton", monoculture_issues[0]["title"])
        
        # Check suggestions contain legume alternative
        self.assertGreater(len(res["suggestions"]), 0)
        legume_suggs = [s for s in res["suggestions"] if "legume" in str(s).lower() or "Fabaceae" in str(s)]
        self.assertGreater(len(legume_suggs), 0)

    def test_repeated_family_solanaceae(self):
        """Potato followed by Tomato (Solanaceae -> Solanaceae) must trigger family repetition alert."""
        farm_info = {"id": 2, "farm_name": "Vegetable Patch", "location": "Kolhapur"}
        history = [
            {"crop_name": "Potato", "planting_date": "2024-11-01", "growth_status": "Harvested"}
        ]
        plans = [
            {"crop_name": "Tomato", "planned_sowing_date": "2025-03-01", "season": "Zaid", "status": "Planned"}
        ]

        res = analyze_crop_rotation_for_farm(farm_info, history, plans)
        self.assertTrue(res["has_sufficient_history"])
        
        family_issues = [i for i in res["issues"] if i["type"] == "REPEATED_FAMILY"]
        self.assertGreater(len(family_issues), 0)
        self.assertEqual(family_issues[0]["family"], "Solanaceae")
        self.assertIn("bacterial wilt", family_issues[0]["description"].lower())

    def test_repeated_family_malvaceae(self):
        """Okra/Bhindi followed by Cotton (Malvaceae -> Malvaceae) triggers pest accumulation alert."""
        farm_info = {"id": 3, "farm_name": "Field 3", "location": "Nagpur"}
        history = [
            {"crop_name": "Okra", "planting_date": "2024-03-01", "growth_status": "Harvested"}
        ]
        plans = [
            {"crop_name": "Cotton", "planned_sowing_date": "2024-07-01", "season": "Kharif", "status": "Planned"}
        ]

        res = analyze_crop_rotation_for_farm(farm_info, history, plans)
        self.assertTrue(res["has_sufficient_history"])
        
        family_issues = [i for i in res["issues"] if i["type"] == "REPEATED_FAMILY"]
        self.assertGreater(len(family_issues), 0)
        self.assertEqual(family_issues[0]["family"], "Malvaceae")
        self.assertIn("bollworm", str(family_issues[0]["risks"]).lower())

    def test_beneficial_legume_rotation(self):
        """Wheat followed by Chickpea/Soybean must be scored favorably with restorative recognition."""
        farm_info = {"id": 4, "farm_name": "Grain Farm", "location": "Indore"}
        history = [
            {"crop_name": "Wheat", "planting_date": "2024-11-15", "growth_status": "Harvested"}
        ]
        plans = [
            {"crop_name": "Chickpea", "planned_sowing_date": "2025-10-15", "season": "Rabi", "status": "Planned"}
        ]

        res = analyze_crop_rotation_for_farm(farm_info, history, plans)
        self.assertTrue(res["has_sufficient_history"])
        self.assertEqual(len(res["issues"]), 0)
        self.assertGreater(len(res["positive_patterns"]), 0)
        self.assertGreaterEqual(res["rotation_score"], 80)
        self.assertEqual(res["rotation_rating"], "Healthy Rotation")


class TestCropRotationRoutes(unittest.TestCase):
    """Test API endpoint and multi-tenant isolation."""

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
        # Clear crop_plans and test crops for users 1 and 2
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM crop_plans WHERE user_id IN (%s, %s)", (self.user1_id, self.user2_id))
        cur.execute("DELETE FROM crops WHERE user_id IN (%s, %s) AND notes LIKE '%%__ROTATION_TEST__%%'", (self.user1_id, self.user2_id))
        conn.commit()
        cur.close()
        conn.close()

    def tearDown(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM crop_plans WHERE user_id IN (%s, %s)", (self.user1_id, self.user2_id))
        cur.execute("DELETE FROM crops WHERE user_id IN (%s, %s) AND notes LIKE '%%__ROTATION_TEST__%%'", (self.user1_id, self.user2_id))
        conn.commit()
        cur.close()
        conn.close()

    def test_unauthenticated_request_rejected(self):
        """Unauthenticated GET /api/crop-plans/rotation-analysis must return 401."""
        res = self.client.get("/api/crop-plans/rotation-analysis")
        self.assertEqual(res.status_code, 401)

    def test_empty_farmer_data_insufficient_history(self):
        """Farmer with no crop records must get clean response with insufficient history."""
        res = self.client.get("/api/crop-plans/rotation-analysis", headers=self.headers1)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("farm_analyses", data)
        # Any farms present with < 2 records should report insufficient history
        for fa in data["farm_analyses"]:
            if fa.get("crop_count", 0) < 2:
                self.assertFalse(fa["has_sufficient_history"])

    def test_farmer_isolation_and_rotation_analysis(self):
        """User 1's plans/crops must not appear in User 2's rotation analysis."""
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        # Find farm for user 1
        cur.execute("SELECT id FROM farms WHERE user_id = %s LIMIT 1", (self.user1_id,))
        f1 = cur.fetchone()
        farm1_id = f1["id"] if f1 else None

        # Insert 2 sequential crops for User 1: Rice then Wheat (continuous Poaceae)
        cur.execute("""
            INSERT INTO crops (user_id, farm_id, crop_name, variety, planting_date, cultivated_area, area_unit, growth_status, notes)
            VALUES (%s, %s, 'Rice', 'Basmati', '2024-06-15', 2.0, 'Acres', 'Harvested', '__ROTATION_TEST__')
        """, (self.user1_id, farm1_id))
        
        cur.execute("""
            INSERT INTO crop_plans (user_id, farm_id, crop_name, variety, season, planning_year, planned_sowing_date, expected_harvest_date, land_area, area_unit, status, notes)
            VALUES (%s, %s, 'Wheat', 'Lokwan', 'Rabi', 2024, '2024-11-20', '2025-03-20', 2.0, 'Acres', 'Planned', '__ROTATION_TEST__')
        """, (self.user1_id, farm1_id))
        conn.commit()
        cur.close()
        conn.close()

        # Query User 1
        url = f"/api/crop-plans/rotation-analysis?farm_id={farm1_id}" if farm1_id else "/api/crop-plans/rotation-analysis"
        res1 = self.client.get(url, headers=self.headers1)
        self.assertEqual(res1.status_code, 200)
        data1 = res1.get_json()
        
        target_farm_analysis = None
        for fa in data1["farm_analyses"]:
            if farm1_id and fa["farm_id"] == farm1_id:
                target_farm_analysis = fa
                break
            elif not farm1_id:
                target_farm_analysis = fa
                break

        self.assertIsNotNone(target_farm_analysis)
        self.assertTrue(target_farm_analysis["has_sufficient_history"])
        self.assertGreaterEqual(target_farm_analysis.get("crop_count", 0), 2)
        # Should identify Poaceae consecutive pattern
        poaceae_issues = [i for i in target_farm_analysis["issues"] if i.get("family") == "Poaceae" or "Poaceae" in str(i)]
        self.assertGreater(len(poaceae_issues), 0)
        # Suggestions should include Fabaceae/legume
        legume_suggs = [s for s in target_farm_analysis["suggestions"] if "legume" in str(s).lower() or "Fabaceae" in str(s)]
        self.assertGreater(len(legume_suggs), 0)

        # Query User 2 - User 1's crops/plans must NOT bleed into User 2
        res2 = self.client.get("/api/crop-plans/rotation-analysis", headers=self.headers2)
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        for fa in data2["farm_analyses"]:
            # Ensure none of user1's crops are present
            timeline_crops = [item["crop_name"] for item in fa.get("timeline", [])]
            self.assertNotIn("__ROTATION_TEST__", str(fa))


if __name__ == "__main__":
    unittest.main()
