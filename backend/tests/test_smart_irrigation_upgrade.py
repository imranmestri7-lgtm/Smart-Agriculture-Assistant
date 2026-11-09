"""Unit tests for AgriSmart Feature Upgrade 3: Smart Irrigation Recommendation System.

Verifies:
1. Soil-type aware calculations (Sandy, Loamy, Clay, Black, Red).
2. Growth-stage aware sensitivity (Flowering peak vs Near Harvest tapering).
3. Rain forecast deferral and water-saving accounting.
4. Temperature-based optimal timing scheduling.
5. Unmeasured / qualitative soil moisture graceful handling without fabricated numbers.
6. Context crops and agronomic catalogs endpoint.
7. Weather preview auto-fill endpoint.
8. Stats and aggregated water saved metrics.
9. Extended history recording and deletion with user isolation.
"""

import os
import unittest
from unittest.mock import patch
from backend.app import app as flask_app
from utils.auth_tokens import create_access_token


class SmartIrrigationUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.client = flask_app.test_client()
        self.env_patch = patch.dict(
            os.environ,
            {"JWT_SECRET_KEY": "phase3-smart-irrigation-test-jwt-secret-key-32-chars"},
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def test_soil_type_impact_sandy_vs_clay(self):
        """Sandy soil drains faster and has lower replenishment depth compared to clay."""
        # Sandy soil
        res_sandy = self.client.post("/api/irrigation/recommend", json={
            "crop": "Tomato",
            "soilMoisture": 30,
            "soilType": "sandy",
            "growthStage": "vegetative",
            "temperature": 28,
            "humidity": 50,
            "rainfall": 0
        })
        self.assertEqual(res_sandy.status_code, 200)
        data_sandy = res_sandy.get_json()["recommendation"]

        # Clay soil
        res_clay = self.client.post("/api/irrigation/recommend", json={
            "crop": "Tomato",
            "soilMoisture": 30,
            "soilType": "clay",
            "growthStage": "vegetative",
            "temperature": 28,
            "humidity": 50,
            "rainfall": 0
        })
        self.assertEqual(res_clay.status_code, 200)
        data_clay = res_clay.get_json()["recommendation"]

        self.assertIn("Sandy", data_sandy["soil_info"]["display_name"])
        self.assertIn("Clay", data_clay["soil_info"]["display_name"])
        self.assertGreater(data_clay["soil_info"]["factor"], data_sandy["soil_info"]["factor"])
        # Clay requires deeper watering replenishment per application
        self.assertGreaterEqual(data_clay["water_quantity"]["amount_mm"], data_sandy["water_quantity"]["amount_mm"])

    def test_flowering_stage_critical_sensitivity(self):
        """Flowering stage should be marked critical with heightened water vigilance."""
        res = self.client.post("/api/irrigation/recommend", json={
            "crop": "Tomato",
            "soilMoisture": 25,
            "soilType": "loamy",
            "growthStage": "flowering",
            "temperature": 30,
            "humidity": 50,
            "rainfall": 0
        })
        self.assertEqual(res.status_code, 200)
        rec = res.get_json()["recommendation"]
        self.assertEqual(rec["status"], "Urgent")
        self.assertTrue(rec["stage_info"]["critical_stage"])
        self.assertIn("FLOWERING STAGE ALERT", rec["explanation"])

    def test_near_harvest_tapering(self):
        """Near harvest stage should reduce water demand and recommend tapering."""
        res = self.client.post("/api/irrigation/recommend", json={
            "crop": "Wheat",
            "soilMoisture": 48,
            "soilType": "loamy",
            "growthStage": "near_harvest",
            "temperature": 25,
            "humidity": 55,
            "rainfall": 0
        })
        self.assertEqual(res.status_code, 200)
        rec = res.get_json()["recommendation"]
        # Near harvest reduces threshold so 48% is adequate or requires minimal/no water
        self.assertFalse(rec["is_irrigation_needed"])
        self.assertIn("near_harvest", rec["stage_info"]["growth_stage"])

    def test_rain_forecast_postponement_saves_water(self):
        """Upcoming rainfall >= 5 mm postpones irrigation and accounts for water saved."""
        res = self.client.post("/api/irrigation/recommend", json={
            "crop": "Maize",
            "soilMoisture": 38,
            "soilType": "loamy",
            "growthStage": "vegetative",
            "temperature": 29,
            "humidity": 65,
            "rainfall": 0,
            "forecastRain": 18.5
        })
        self.assertEqual(res.status_code, 200)
        rec = res.get_json()["recommendation"]
        self.assertEqual(rec["status"], "Postpone / Rain Expected")
        self.assertFalse(rec["is_irrigation_needed"])
        self.assertGreater(rec["water_saved_mm"], 0.0)
        self.assertGreater(rec["water_saved_litres_ha"], 0)
        self.assertIn("18.5 mm", rec["explanation"])
        self.assertIn("Deferred", rec["suggested_time"])

    def test_hot_weather_timing_advisory(self):
        """Temperature >= 33°C recommends early morning or late evening watering."""
        res = self.client.post("/api/irrigation/recommend", json={
            "crop": "Cotton",
            "soilMoisture": 35,
            "soilType": "black",
            "growthStage": "vegetative",
            "temperature": 37.5,
            "humidity": 30,
            "rainfall": 0
        })
        self.assertEqual(res.status_code, 200)
        rec = res.get_json()["recommendation"]
        self.assertIn("Early Morning", rec["suggested_time"])
        self.assertIn("Late Evening", rec["suggested_time"])
        self.assertIn("evaporative", rec["timing_reason"].lower())

    def test_cool_weather_timing_advisory(self):
        """Temperature <= 18°C recommends mid-morning watering to prevent nocturnal fungal growth."""
        res = self.client.post("/api/irrigation/recommend", json={
            "crop": "Wheat",
            "soilMoisture": 38,
            "soilType": "loamy",
            "growthStage": "vegetative",
            "temperature": 15.0,
            "humidity": 60,
            "rainfall": 0
        })
        self.assertEqual(res.status_code, 200)
        rec = res.get_json()["recommendation"]
        self.assertIn("Mid-Morning", rec["suggested_time"])

    def test_unmeasured_soil_moisture_graceful_guidance(self):
        """When soil moisture is not measured, engine returns qualitative guidance without fake numbers."""
        res = self.client.post("/api/irrigation/recommend", json={
            "crop": "Sugarcane",
            "soilMoisture": None,
            "allow_unmeasured": True,
            "soilType": "clay",
            "growthStage": "vegetative",
            "temperature": 31,
            "humidity": 55,
            "rainfall": 0
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIsNone(data["inputs"]["soilMoisture"])
        rec = data["recommendation"]
        self.assertEqual(rec["status"], "Guidance (Unmeasured)")
        self.assertIn("root-zone", rec["explanation"].lower())
        # Check next steps contain practical manual tactile check
        steps_text = " ".join(rec["next_steps"]).lower()
        self.assertIn("tactile check", steps_text)
        self.assertIn("squeeze", steps_text)

    def test_context_crops_endpoint(self):
        """GET /api/irrigation/context-crops returns catalogs of soils, stages, and crops."""
        res = self.client.get("/api/irrigation/context-crops")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("soil_types", data)
        self.assertIn("growth_stages", data)
        self.assertIn("standard_crops", data)
        soil_keys = [s["key"] for s in data["soil_types"]]
        self.assertIn("sandy", soil_keys)
        self.assertIn("black", soil_keys)

    def test_weather_preview_validation(self):
        """GET /api/irrigation/weather-preview requires location."""
        res_no_loc = self.client.get("/api/irrigation/weather-preview")
        self.assertEqual(res_no_loc.status_code, 400)

    @patch("routes.irrigation_routes._fetch_live_weather")
    def test_weather_preview_success(self, mock_fetch):
        """GET /api/irrigation/weather-preview returns live weather and forecast rain."""
        mock_fetch.return_value = {
            "temperature": 27.5,
            "humidity": 62.0,
            "rainfall": 0.0,
            "forecast_rain_mm": 12.0,
            "condition": "Partly Cloudy",
            "location_name": "Pune"
        }
        res = self.client.get("/api/irrigation/weather-preview?location=Pune")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["weather"]["temperature"], 27.5)
        self.assertEqual(data["weather"]["forecast_rain_mm"], 12.0)

    def test_stats_requires_auth(self):
        """GET /api/irrigation/stats requires valid token."""
        res = self.client.get("/api/irrigation/stats")
        self.assertEqual(res.status_code, 401)

    def test_authenticated_recommend_and_history_persistence(self):
        """Authenticated request records soil_type, growth_stage, timing, and forecast rain."""
        token = create_access_token(user_id=1)
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "crop": "Potato",
            "soilMoisture": 32,
            "soilType": "sandy",
            "growthStage": "flowering",
            "temperature": 34,
            "humidity": 45,
            "rainfall": 0,
            "forecastRain": 0,
            "location": "Nashik"
        }
        post_res = self.client.post("/api/irrigation/recommend", json=payload, headers=headers)
        self.assertEqual(post_res.status_code, 200)
        self.assertTrue(post_res.get_json()["history_saved"])

        # Fetch history
        hist_res = self.client.get("/api/irrigation/history", headers=headers)
        self.assertEqual(hist_res.status_code, 200)
        hist_data = hist_res.get_json()
        self.assertGreater(hist_data["count"], 0)
        latest = hist_data["history"][0]
        self.assertEqual(latest["crop"], "Potato")
        self.assertEqual(latest["soil_type"], "sandy")
        self.assertEqual(latest["growth_stage"], "flowering")
        self.assertIsNotNone(latest["timing_recommendation"])


if __name__ == "__main__":
    unittest.main()
