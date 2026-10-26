import os
import unittest
from unittest.mock import patch

from backend.app import app as flask_app
from utils.auth_tokens import create_access_token
from utils.chatbot import generate_response


class Phase4Tests(unittest.TestCase):
    def setUp(self):
        self.client = flask_app.test_client()
        self.env_patch = patch.dict(
            os.environ,
            {"JWT_SECRET_KEY": "phase4-test-secret-for-unit-tests"},
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def headers(self):
        token = create_access_token(123)
        return {"Authorization": f"Bearer {token}"}

    def test_chat_requires_authentication(self):
        response = self.client.post(
            "/api/chat/message",
            json={"message": "How should I water my crop?"},
        )
        self.assertEqual(response.status_code, 401)

    def test_chat_rejects_invalid_token(self):
        response = self.client.post(
            "/api/chat/message",
            headers={"Authorization": "Bearer invalid-token"},
            json={"message": "How should I water my crop?"},
        )
        self.assertEqual(response.status_code, 401)

    def test_chat_rejects_empty_message(self):
        response = self.client.post(
            "/api/chat/message",
            headers=self.headers(),
            json={"message": "   "},
        )
        self.assertEqual(response.status_code, 400)

    def test_chat_rejects_oversized_message(self):
        response = self.client.post(
            "/api/chat/message",
            headers=self.headers(),
            json={"message": "x" * 1001},
        )
        self.assertEqual(response.status_code, 400)

    def test_chat_answers_irrigation_question(self):
        response = self.client.post(
            "/api/chat/message",
            headers=self.headers(),
            json={"message": "How should I manage irrigation?"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["category"], "irrigation")
        self.assertIn("soil moisture", data["reply"].lower())

    def test_chat_answers_disease_question(self):
        result = generate_response("How do I identify a plant disease?")
        self.assertEqual(result["category"], "disease")
        self.assertIn("prediction", result["reply"].lower())

    def test_chat_answers_weather_question(self):
        result = generate_response("Can you give me a weather forecast?")
        self.assertEqual(result["category"], "weather")
        self.assertIn("Weather section", result["reply"])

    def test_chat_general_fallback(self):
        result = generate_response("I need farming guidance")
        self.assertEqual(result["category"], "general")
        self.assertTrue(result["reply"])


if __name__ == "__main__":
    unittest.main()
