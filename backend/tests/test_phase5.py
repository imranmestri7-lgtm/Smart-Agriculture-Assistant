import unittest
import json
from utils.chatbot import MAX_MESSAGE_LENGTH
import os
from datetime import timedelta

# Ensure the app can import utilities
try:
    from backend.app import app
except ImportError:
    from app import app
from utils.auth_tokens import create_access_token

class Phase5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a test client for the Flask app
        cls.client = app.test_client()
        # Generate a valid JWT for user id 1 (assuming user exists in test DB)
        cls.token = create_access_token(1)
        cls.auth_header = {"Authorization": f"Bearer {cls.token}"}

    def test_missing_auth_header(self):
        response = self.client.post('/api/chat/message', json={"message": "Hello"})
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn("error", data.get("status", ""))

    def test_invalid_token(self):
        headers = {"Authorization": "Bearer invalidtoken"}
        response = self.client.post('/api/chat/message', json={"message": "Hello"}, headers=headers)
        self.assertEqual(response.status_code, 401)

    def test_empty_body(self):
        response = self.client.post('/api/chat/message', json={}, headers=self.auth_header)
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn("Please enter a farming question.", data.get("message", ""))

    def test_empty_message(self):
        response = self.client.post('/api/chat/message', json={"message": "   "}, headers=self.auth_header)
        self.assertEqual(response.status_code, 400)

    def test_oversized_message(self):
        long_msg = "a" * (MAX_MESSAGE_LENGTH + 1)
        response = self.client.post('/api/chat/message', json={"message": long_msg}, headers=self.auth_header)
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn(str(MAX_MESSAGE_LENGTH), data.get("message", ""))

    def test_greeting_intent(self):
        response = self.client.post('/api/chat/message', json={"message": "Hi there"}, headers=self.auth_header)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("category"), "greeting")
        self.assertIn("Hello", data.get("reply", ""))

    def test_irrigation_intent_fuzzy(self):
        # misspelled "irrigation"
        response = self.client.post('/api/chat/message', json={"message": "How much irrigtion do I need?"}, headers=self.auth_header)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("category"), "irrigation")
        self.assertIn("irrig", data.get("reply", "").lower())

    def test_disease_intent_known(self):
        # Use a known disease class name from knowledge base
        response = self.client.post('/api/chat/message', json={"message": "Tomato___Early_blight"}, headers=self.auth_header)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("category"), "disease")
        # The reply should contain the disease display name
        self.assertIn("Early blight", data.get("reply", ""))
        # Knowledge field should be present in the internal response (tested via utils directly)
        # Verify generate_response returns knowledge
        from utils.chatbot import generate_response
        result = generate_response("Tomato___Early_blight")
        self.assertIn("knowledge", result)
        self.assertIsInstance(result["knowledge"], dict)

    def test_disease_intent_unknown(self):
        response = self.client.post('/api/chat/message', json={"message": "UnknownDiseaseXYZ"}, headers=self.auth_header)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("category"), "unknown")
        self.assertIn("Upload a clear photo", data.get("reply", ""))

    def test_crop_intent_follow_up(self):
        response = self.client.post('/api/chat/message', json={"message": "I grow wheat"}, headers=self.auth_header)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("category"), "crop")
        # follow_up may be returned in internal result, check via direct call
        from utils.chatbot import generate_response
        result = generate_response("I grow wheat")
        self.assertIn("follow_up", result)
        self.assertIsInstance(result["follow_up"], str)

    def test_weather_intent(self):
        response = self.client.post('/api/chat/message', json={"message": "What's the weather today?"}, headers=self.auth_header)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("category"), "weather")

    def test_market_intent(self):
        response = self.client.post('/api/chat/message', json={"message": "Current market price for corn"}, headers=self.auth_header)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get("category"), "market")

if __name__ == '__main__':
    unittest.main()
