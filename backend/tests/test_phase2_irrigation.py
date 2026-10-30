import unittest
import os
from unittest.mock import patch
from backend.app import app as flask_app
from utils.auth_tokens import create_access_token


class Phase2SmartIrrigationTests(unittest.TestCase):
    def setUp(self):
        self.client = flask_app.test_client()
        self.env_patch = patch.dict(
            os.environ,
            {"JWT_SECRET_KEY": "phase2-test-jwt-secret-at-least-32-chars-long"},
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def test_valid_irrigation_request_urgent(self):
        """Test Urgent status when soil moisture is critically low."""
        payload = {
            "crop": "Tomato",
            "soilMoisture": 25,
            "temperature": 32,
            "humidity": 45,
            "rainfall": 0,
            "location": "Maharashtra"
        }
        res = self.client.post("/api/irrigation/recommend", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "success")
        rec = data.get("recommendation", {})
        self.assertEqual(rec.get("status"), "Urgent")
        self.assertTrue(rec.get("is_irrigation_needed"))
        self.assertGreater(rec["water_quantity"]["amount_mm"], 0)
        self.assertIn("Critical", rec.get("explanation", ""))
        self.assertIsInstance(rec.get("next_steps"), list)
        self.assertGreater(len(rec.get("next_steps")), 0)

    def test_valid_irrigation_request_recommended(self):
        """Test Recommended status when soil moisture is below optimal but above wilting threshold."""
        payload = {
            "crop": "Wheat",
            "soilMoisture": 42,
            "temperature": 25,
            "humidity": 55,
            "rainfall": 2,
            "location": "Punjab"
        }
        res = self.client.post("/api/irrigation/recommend", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        rec = data.get("recommendation", {})
        self.assertEqual(rec.get("status"), "Recommended")
        self.assertTrue(rec.get("is_irrigation_needed"))
        self.assertGreater(rec["water_quantity"]["amount_mm"], 0)
        self.assertIn("Recommended", rec.get("status"))

    def test_valid_irrigation_request_adequate(self):
        """Test Adequate status when soil moisture is within optimal range."""
        payload = {
            "crop": "Maize",
            "soilMoisture": 58,
            "temperature": 26,
            "humidity": 60,
            "rainfall": 5
        }
        res = self.client.post("/api/irrigation/recommend", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        rec = data.get("recommendation", {})
        self.assertEqual(rec.get("status"), "Adequate")
        self.assertFalse(rec.get("is_irrigation_needed"))
        self.assertEqual(rec["water_quantity"]["amount_mm"], 0.0)

    def test_valid_irrigation_request_overwatered(self):
        """Test Overwatered status when soil is saturated."""
        payload = {
            "crop": "Cotton",
            "soilMoisture": 85,
            "temperature": 28,
            "humidity": 75,
            "rainfall": 30
        }
        res = self.client.post("/api/irrigation/recommend", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        rec = data.get("recommendation", {})
        self.assertEqual(rec.get("status"), "Overwatered")
        self.assertFalse(rec.get("is_irrigation_needed"))
        self.assertEqual(rec["water_quantity"]["amount_mm"], 0.0)
        self.assertIn("surface drainage", " ".join(rec.get("next_steps", [])))

    def test_missing_crop(self):
        """Test missing crop returns 400."""
        payload = {
            "soilMoisture": 30,
            "temperature": 28,
            "humidity": 60,
            "rainfall": 0
        }
        res = self.client.post("/api/irrigation/recommend", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data.get("status"), "error")
        self.assertIn("Crop name is required", data.get("message", ""))

    def test_empty_crop_string(self):
        """Test empty whitespace crop returns 400."""
        payload = {
            "crop": "   ",
            "soilMoisture": 30,
            "temperature": 28,
            "humidity": 60,
            "rainfall": 0
        }
        res = self.client.post("/api/irrigation/recommend", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Crop name is required", res.get_json().get("message", ""))

    def test_missing_required_measurements(self):
        """Test missing temperature and rainfall returns 400."""
        payload = {
            "crop": "Rice",
            "soilMoisture": 40,
            "humidity": 70
        }
        res = self.client.post("/api/irrigation/recommend", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data.get("status"), "error")
        self.assertIn("Missing required measurements", data.get("message", ""))

    def test_invalid_moisture_percentage(self):
        """Test negative soil moisture returns 400."""
        payload = {
            "crop": "Rice",
            "soilMoisture": -5,
            "temperature": 25,
            "humidity": 60,
            "rainfall": 0
        }
        res = self.client.post("/api/irrigation/recommend", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("between 0% and 100%", res.get_json().get("message", ""))

        # Test moisture > 100
        payload["soilMoisture"] = 105
        res = self.client.post("/api/irrigation/recommend", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("between 0% and 100%", res.get_json().get("message", ""))

    def test_invalid_temperature(self):
        """Test temperature outside -10 to 60°C returns 400."""
        payload = {
            "crop": "Wheat",
            "soilMoisture": 40,
            "temperature": 75,
            "humidity": 50,
            "rainfall": 0
        }
        res = self.client.post("/api/irrigation/recommend", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("between -10°C and 60°C", res.get_json().get("message", ""))

        payload["temperature"] = -25
        res = self.client.post("/api/irrigation/recommend", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("between -10°C and 60°C", res.get_json().get("message", ""))

    def test_invalid_humidity(self):
        """Test humidity outside 0 to 100% returns 400."""
        payload = {
            "crop": "Sugarcane",
            "soilMoisture": 50,
            "temperature": 30,
            "humidity": 120,
            "rainfall": 0
        }
        res = self.client.post("/api/irrigation/recommend", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Humidity must be a number between 0% and 100%", res.get_json().get("message", ""))

    def test_negative_rainfall(self):
        """Test negative rainfall returns 400."""
        payload = {
            "crop": "Potato",
            "soilMoisture": 50,
            "temperature": 22,
            "humidity": 65,
            "rainfall": -10
        }
        res = self.client.post("/api/irrigation/recommend", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("non-negative number", res.get_json().get("message", ""))

    def test_non_json_body(self):
        """Test non-JSON body returns 400."""
        res = self.client.post("/api/irrigation/recommend", data="plain text body")
        self.assertEqual(res.status_code, 400)

    def test_non_numeric_values(self):
        """Test non-numeric strings for numbers returns 400."""
        payload = {
            "crop": "Potato",
            "soilMoisture": "high",
            "temperature": 22,
            "humidity": 65,
            "rainfall": 0
        }
        res = self.client.post("/api/irrigation/recommend", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("must be numeric values", res.get_json().get("message", ""))

    def test_authenticated_request_saves_history(self):
        """Test that a valid JWT token associates recommendation with authenticated user."""
        token = create_access_token(user_id=1)
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "crop": "Tomato",
            "soilMoisture": 30,
            "temperature": 28,
            "humidity": 50,
            "rainfall": 0,
            "location": "Maharashtra"
        }
        res = self.client.post("/api/irrigation/recommend", json=payload, headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("history_saved", data)

    def test_history_endpoint_requires_auth(self):
        """Test GET /api/irrigation/history requires a valid token."""
        res_no_auth = self.client.get("/api/irrigation/history")
        self.assertEqual(res_no_auth.status_code, 401)

        res_bad_token = self.client.get(
            "/api/irrigation/history",
            headers={"Authorization": "Bearer invalid.token.value"}
        )
        self.assertEqual(res_bad_token.status_code, 401)


if __name__ == "__main__":
    unittest.main()
