"""
Unit & Integration Tests for Seasonal & Soil-Aware Crop Recommendations
(Feature Upgrade 9, Phase 2 Part 2)

Tests:
1. Seasonal suggestions (Kharif, Rabi, Zaid, all seasons)
2. Soil compatibility evaluation (Black Cotton, Sandy Loam, Clay, Loamy, Red)
3. Unsuitable soil detection with clear agronomic reasoning (e.g. Groundnut in Black Clay)
4. Missing soil information handling (clear limitation notice + general regional advice)
5. Crop history integration (monoculture and family repetition hazards, legume benefits)
6. API endpoints GET /api/crop-plans/recommendations and GET /api/crop/recommendations
7. Strict multi-tenant farmer data isolation (JWT verification, user_id boundary)
"""

import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from config import get_db_connection
from utils.auth_tokens import create_access_token
from utils.seasonal_crop_advisor import (
    normalize_soil_type,
    get_current_indian_season,
    evaluate_soil_compatibility,
    evaluate_rotation_impact,
    generate_seasonal_crop_recommendations,
    MAHARASHTRA_CROP_CATALOG
)


class TestSeasonalCropAdvisorUnit(unittest.TestCase):
    """Unit tests for agronomic evaluation functions."""

    def test_soil_normalization(self):
        """Test soil normalization for English, Marathi, and Hindi aliases."""
        self.assertEqual(normalize_soil_type("Black"), "black")
        self.assertEqual(normalize_soil_type("black cotton"), "black")
        self.assertEqual(normalize_soil_type("काळी कापशी जमीन"), "black")
        self.assertEqual(normalize_soil_type("काली मिट्टी"), "black")
        self.assertEqual(normalize_soil_type("Regur"), "black")

        self.assertEqual(normalize_soil_type("Sandy Loam"), "sandy")
        self.assertEqual(normalize_soil_type("रेतीली मिट्टी"), "sandy")
        self.assertEqual(normalize_soil_type("वाळूयुक्त जमीन"), "sandy")

        self.assertEqual(normalize_soil_type("Loamy"), "loamy")
        self.assertEqual(normalize_soil_type("alluvial"), "loamy")
        self.assertEqual(normalize_soil_type("दोमट मिट्टी"), "loamy")

        self.assertEqual(normalize_soil_type("Clay"), "clay")
        self.assertEqual(normalize_soil_type("Red"), "red")
        self.assertIsNone(normalize_soil_type("Unknown Martian Dust"))

    def test_current_indian_season(self):
        """Test seasonal calculation across calendar months."""
        self.assertEqual(get_current_indian_season(date(2026, 7, 15)), "Kharif")
        self.assertEqual(get_current_indian_season(date(2026, 8, 20)), "Kharif")
        self.assertEqual(get_current_indian_season(date(2026, 11, 10)), "Rabi")
        self.assertEqual(get_current_indian_season(date(2026, 1, 15)), "Rabi")
        self.assertEqual(get_current_indian_season(date(2026, 3, 20)), "Zaid")
        self.assertEqual(get_current_indian_season(date(2026, 5, 10)), "Zaid")

    def test_soil_compatibility_black_cotton(self):
        """Cotton & Chickpea must be Optimal in Black soil, Groundnut must be Unsuitable."""
        cotton_def = next(c for c in MAHARASHTRA_CROP_CATALOG if c["crop_name"] == "Cotton")
        compat, score, reason = evaluate_soil_compatibility(cotton_def, "black")
        self.assertEqual(compat, "Optimal")
        self.assertGreaterEqual(score, 90)
        self.assertIn("black", reason.lower())

        groundnut_def = next(c for c in MAHARASHTRA_CROP_CATALOG if c["crop_name"] == "Groundnut")
        gn_compat, gn_score, gn_reason = evaluate_soil_compatibility(groundnut_def, "black")
        self.assertEqual(gn_compat, "Unsuitable")
        self.assertLessEqual(gn_score, 30)
        self.assertTrue("peg" in gn_reason.lower() or "clod" in gn_reason.lower() or "breakage" in gn_reason.lower() or "pod" in gn_reason.lower())

    def test_soil_compatibility_sandy_soil(self):
        """Groundnut & Watermelon must be Optimal in Sandy soil; Cotton must be Unsuitable."""
        gn_def = next(c for c in MAHARASHTRA_CROP_CATALOG if c["crop_name"] == "Groundnut")
        compat, score, reason = evaluate_soil_compatibility(gn_def, "sandy")
        self.assertEqual(compat, "Optimal")
        self.assertGreaterEqual(score, 90)

        wm_def = next(c for c in MAHARASHTRA_CROP_CATALOG if c["crop_name"] == "Watermelon")
        wm_compat, wm_score, _ = evaluate_soil_compatibility(wm_def, "sandy")
        self.assertEqual(wm_compat, "Optimal")
        self.assertGreaterEqual(wm_score, 90)

        cotton_def = next(c for c in MAHARASHTRA_CROP_CATALOG if c["crop_name"] == "Cotton")
        cot_compat, cot_score, _ = evaluate_soil_compatibility(cotton_def, "sandy")
        self.assertEqual(cot_compat, "Unsuitable")
        self.assertLessEqual(cot_score, 30)

    def test_soil_compatibility_missing_soil(self):
        """Missing soil must return general guidance with limitation note."""
        wheat_def = next(c for c in MAHARASHTRA_CROP_CATALOG if c["crop_name"] == "Wheat")
        compat, score, reason = evaluate_soil_compatibility(wheat_def, None)
        self.assertIn("General", compat)
        self.assertIn("Soil Unknown", compat)
        self.assertEqual(score, 70)
        self.assertIn("not registered", reason.lower())

    def test_rotation_hazard_monoculture(self):
        """Recommending Cotton when Cotton was previous crop must flag rotation hazard."""
        cotton_def = next(c for c in MAHARASHTRA_CROP_CATALOG if c["crop_name"] == "Cotton")
        prev = {"crop_name": "Cotton", "family": "Malvaceae"}
        res = evaluate_rotation_impact(cotton_def, prev)
        self.assertTrue(res["is_rotation_hazard"])
        self.assertEqual(res["rotation_status"], "Rotation Hazard")
        self.assertEqual(res["rotation_risk_level"], "HIGH")
        self.assertIn("Monoculture", res["rotation_notes"])
        self.assertGreater(len(res["alternatives"]), 0)

    def test_rotation_hazard_family_repetition(self):
        """Recommending Tomato when Potato was previous crop must flag Solanaceae warning."""
        tomato_def = {
            "crop_name": "Tomato",
            "family": "Solanaceae",
            "alternatives": ["Chickpea", "Soybean"]
        }
        prev = {"crop_name": "Potato", "family": "Solanaceae"}
        res = evaluate_rotation_impact(tomato_def, prev)
        self.assertTrue(res["is_rotation_hazard"])
        self.assertEqual(res["rotation_status"], "Rotation Hazard")
        self.assertIn("Solanaceae", res["rotation_notes"])
        self.assertIn("Bacterial Wilt", res["rotation_notes"])

    def test_rotation_benefit_legume_after_cereal(self):
        """Recommending Chickpea (Fabaceae) after Wheat (Poaceae) must be flagged beneficial."""
        chickpea_def = next(c for c in MAHARASHTRA_CROP_CATALOG if c["crop_name"] == "Chickpea")
        prev = {"crop_name": "Wheat", "family": "Poaceae"}
        res = evaluate_rotation_impact(chickpea_def, prev)
        self.assertTrue(res["is_rotation_benefit"])
        self.assertFalse(res["is_rotation_hazard"])
        self.assertEqual(res["rotation_status"], "Recommended Rotation")
        self.assertIn("nitrogen", res["rotation_notes"].lower())


class TestSeasonalCropAdvisorRoutes(unittest.TestCase):
    """Integration tests for crop recommendation endpoints and farmer isolation."""

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
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM crop_plans WHERE user_id IN (%s, %s) AND notes LIKE '%%__REC_TEST__%%'", (self.user1_id, self.user2_id))
        cur.execute("DELETE FROM crops WHERE user_id IN (%s, %s) AND notes LIKE '%%__REC_TEST__%%'", (self.user1_id, self.user2_id))
        cur.execute("DELETE FROM farms WHERE user_id IN (%s, %s) AND farm_name LIKE '%%__REC_FARM__%%'", (self.user1_id, self.user2_id))
        conn.commit()
        cur.close()
        conn.close()

    def tearDown(self):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM crop_plans WHERE user_id IN (%s, %s) AND notes LIKE '%%__REC_TEST__%%'", (self.user1_id, self.user2_id))
        cur.execute("DELETE FROM crops WHERE user_id IN (%s, %s) AND notes LIKE '%%__REC_TEST__%%'", (self.user1_id, self.user2_id))
        cur.execute("DELETE FROM farms WHERE user_id IN (%s, %s) AND farm_name LIKE '%%__REC_FARM__%%'", (self.user1_id, self.user2_id))
        conn.commit()
        cur.close()
        conn.close()

    def test_unauthenticated_requests_rejected(self):
        """Unauthenticated requests must be rejected with 401."""
        res1 = self.client.get("/api/crop-plans/recommendations")
        self.assertEqual(res1.status_code, 401)

        res2 = self.client.get("/api/crop/recommendations")
        self.assertEqual(res2.status_code, 401)

    def test_seasonal_filtering_kharif_rabi_zaid(self):
        """Filtering by season must restrict recommended crops accordingly."""
        # Kharif filter
        res_k = self.client.get("/api/crop-plans/recommendations?season=Kharif", headers=self.headers1)
        self.assertEqual(res_k.status_code, 200)
        data_k = res_k.get_json()
        self.assertEqual(data_k["selected_season"], "Kharif")
        self.assertGreater(data_k["recommendations_count"], 0)
        for rec in data_k["recommendations"]:
            self.assertEqual(rec["season"], "Kharif")
            self.assertTrue(rec["sowing_window"])
            self.assertTrue(rec["crop_duration"])

        # Rabi filter
        res_r = self.client.get("/api/crop-plans/recommendations?season=Rabi", headers=self.headers1)
        self.assertEqual(res_r.status_code, 200)
        data_r = res_r.get_json()
        self.assertEqual(data_r["selected_season"], "Rabi")
        for rec in data_r["recommendations"]:
            self.assertEqual(rec["season"], "Rabi")

        # Zaid filter
        res_z = self.client.get("/api/crop-plans/recommendations?season=Zaid", headers=self.headers1)
        self.assertEqual(res_z.status_code, 200)
        data_z = res_z.get_json()
        self.assertEqual(data_z["selected_season"], "Zaid")
        for rec in data_z["recommendations"]:
            self.assertEqual(rec["season"], "Zaid")

    def test_soil_override_and_missing_soil_handling(self):
        """Check behavior when soil type is provided vs missing."""
        # Missing soil
        res_no_soil = self.client.get("/api/crop-plans/recommendations?soil_type=", headers=self.headers1)
        self.assertEqual(res_no_soil.status_code, 200)
        data_no_soil = res_no_soil.get_json()
        if not data_no_soil["farm_context"]["soil_known"]:
            self.assertIsNotNone(data_no_soil["farm_context"]["soil_limitation_notice"])
            self.assertIn("Soil type is not registered", data_no_soil["farm_context"]["soil_limitation_notice"])

        # Black soil override
        res_black = self.client.get("/api/crop-plans/recommendations?season=Kharif&soil_type=black", headers=self.headers1)
        self.assertEqual(res_black.status_code, 200)
        data_black = res_black.get_json()
        self.assertTrue(data_black["farm_context"]["soil_known"])
        self.assertEqual(data_black["farm_context"]["soil_type"], "black")

        # Top ranked Kharif crops in Black soil should be Cotton or Soybean
        top_crop = data_black["recommendations"][0]
        self.assertIn(top_crop["crop_name"], ["Soybean", "Cotton", "Pigeon Pea"])
        self.assertEqual(top_crop["soil_compatibility"], "Optimal")

    def test_crop_history_integration_and_farmer_isolation(self):
        """User 1's previous crops trigger rotation warnings for User 1, but not for User 2."""
        conn = get_db_connection()
        cur = conn.cursor()
        # Create a farm for user 1 with black soil
        cur.execute("""
            INSERT INTO farms (user_id, farm_name, location, total_area, area_unit, soil_type)
            VALUES (%s, '__REC_FARM__ Black Soil Plot', 'Nashik, Maharashtra', 10.0, 'Acres', 'black')
        """, (self.user1_id,))
        farm1_id = cur.lastrowid

        # Insert historical Cotton crop for User 1
        cur.execute("""
            INSERT INTO crops (user_id, farm_id, crop_name, variety, planting_date, cultivated_area, area_unit, growth_status, notes)
            VALUES (%s, %s, 'Cotton', 'Bt-Cotton', '2024-06-15', 5.0, 'Acres', 'Harvested', '__REC_TEST__')
        """, (self.user1_id, farm1_id))

        conn.commit()
        cur.close()
        conn.close()

        # Query User 1 recommendations for farm1
        res1 = self.client.get(f"/api/crop-plans/recommendations?farm_id={farm1_id}&season=Kharif", headers=self.headers1)
        self.assertEqual(res1.status_code, 200)
        data1 = res1.get_json()
        self.assertEqual(data1["farm_context"]["farm_id"], farm1_id)
        self.assertIsNotNone(data1["farm_context"]["previous_crop"])
        self.assertEqual(data1["farm_context"]["previous_crop"]["crop_name"], "Cotton")

        # Cotton should be flagged as Rotation Hazard
        cotton_rec = next(r for r in data1["recommendations"] if r["crop_name"] == "Cotton")
        self.assertTrue(cotton_rec["is_rotation_hazard"])
        self.assertEqual(cotton_rec["rotation_status"], "Rotation Hazard")
        self.assertIn("Monoculture", cotton_rec["rotation_notes"])
        self.assertGreater(len(cotton_rec["alternatives"]), 0)

        # Legumes (Soybean, Tur) should NOT have rotation hazard
        soybean_rec = next(r for r in data1["recommendations"] if r["crop_name"] == "Soybean")
        self.assertFalse(soybean_rec["is_rotation_hazard"])
        self.assertEqual(soybean_rec["soil_compatibility"], "Optimal")

        # Multi-tenant isolation: User 2 must NOT be able to query User 1's farm_id
        res2_hack = self.client.get(f"/api/crop-plans/recommendations?farm_id={farm1_id}", headers=self.headers2)
        self.assertEqual(res2_hack.status_code, 404)

        # User 2 normal query should have independent context
        res2 = self.client.get("/api/crop-plans/recommendations?season=Kharif", headers=self.headers2)
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        # Cotton for user 2 should not have user 1's cotton history warning
        cot2 = next((r for r in data2["recommendations"] if r["crop_name"] == "Cotton"), None)
        if cot2 and not data2["farm_context"]["previous_crop"]:
            self.assertFalse(cot2["is_rotation_hazard"])


if __name__ == "__main__":
    unittest.main()
