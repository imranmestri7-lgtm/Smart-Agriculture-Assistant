import unittest
from backend.app import app as flask_app


class Phase1BlueprintTests(unittest.TestCase):
    def setUp(self):
        self.client = flask_app.test_client()

    def test_registered_blueprints(self):
        """Verify that all required blueprints are registered with Flask."""
        registered = set(flask_app.blueprints.keys())
        expected = {"auth", "chat", "disease", "irrigation", "weather", "crop"}
        self.assertTrue(expected.issubset(registered), f"Missing blueprints: {expected - registered}")

    def test_home_and_test_endpoints(self):
        """Verify standard health check endpoints."""
        res_home = self.client.get("/")
        self.assertEqual(res_home.status_code, 200)
        self.assertIn("message", res_home.get_json())

        res_test = self.client.get("/api/test")
        self.assertEqual(res_test.status_code, 200)
        self.assertEqual(res_test.get_json().get("status"), "success")

    def test_crop_recommendation_success(self):
        """Test POST /api/crop/recommend with valid nutrient levels."""
        payload = {
            "nitrogen": 90,
            "phosphorus": 85,
            "potassium": 85
        }
        res = self.client.post("/api/crop/recommend", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "success")
        self.assertEqual(data.get("recommendation"), "Rice")

    def test_crop_recommendation_missing_fields(self):
        """Test POST /api/crop/recommend with missing fields returns 400."""
        res = self.client.post("/api/crop/recommend", json={"nitrogen": 50})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data.get("status"), "error")
        self.assertIn("Missing required fields", data.get("message", ""))

    def test_crop_recommendation_invalid_values(self):
        """Test POST /api/crop/recommend with non-numeric fields returns 400."""
        payload = {
            "nitrogen": "invalid",
            "phosphorus": 50,
            "potassium": 50
        }
        res = self.client.post("/api/crop/recommend", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data.get("status"), "error")
        self.assertIn("Nutrient values must be numbers", data.get("message", ""))

    def test_weather_search_short_query(self):
        """Test GET /api/weather/search with query < 2 chars returns empty list."""
        res = self.client.get("/api/weather/search?q=a")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json(), [])

    def test_weather_forecast_missing_query(self):
        """Test GET /api/weather/forecast without 'q' parameter returns 400."""
        res = self.client.get("/api/weather/forecast")
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data.get("status"), "error")
        self.assertIn("Location query parameter 'q' is required", data.get("message", ""))

    def test_weather_search_live(self):
        """Test GET /api/weather/search with query 'Pune' returns search results or clear error if key invalid."""
        res = self.client.get("/api/weather/search?q=Pune")
        data = res.get_json()
        if res.status_code == 200:
            self.assertIsInstance(data, list)
            if data:
                self.assertIn("name", data[0])
        else:
            # If weather provider is down or key unconfigured
            self.assertIn(res.status_code, [502, 503])
            self.assertEqual(data.get("status"), "error")

    def test_weather_forecast_live(self):
        """Test GET /api/weather/forecast with 'Pune' returns forecast data or clear error."""
        res = self.client.get("/api/weather/forecast?q=Pune&days=3")
        data = res.get_json()
        if res.status_code == 200:
            self.assertIn("current", data)
            self.assertIn("forecast", data)
        else:
            self.assertIn(res.status_code, [502, 503])
            self.assertEqual(data.get("status"), "error")


if __name__ == "__main__":
    unittest.main()
