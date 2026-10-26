import unittest
from unittest.mock import patch

from utils import chatbot
from utils.auth_tokens import create_access_token
from backend.app import app as flask_app

class DiseaseResponseTests(unittest.TestCase):
    def setUp(self):
        self.client = flask_app.test_client()
        self.token = create_access_token(user_id=1)

    def _post(self, message, language=None):
        payload = {"message": message}
        if language:
            payload["language"] = language
        return self.client.post(
            "/api/chat/message",
            json=payload,
            headers={"Authorization": f"Bearer {self.token}"},
        )

    def test_high_confidence_detailed_reply(self):
        # Use exact class name to ensure known_class detection
        resp = self._post("Tomato___Early_blight")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["category"], "disease")
        # reply should contain several sections
        reply = data["reply"]
        for header in ["Symptoms:", "Possible causes:", "Prevention / care recommendations:", "Safe treatment suggestions:", "Disclaimer:"]:
            self.assertIn(header, reply)
        # low confidence follow_up should NOT be present
        self.assertNotIn("follow_up", data)

    def test_low_confidence_follow_up(self):
        # Patch get_disease_info to return a dict with is_uncertain=True
        mock_knowledge = {
            "display_name": "Test Disease",
            "description": "Test description.",
            "symptoms": ["sym1"],
            "possible_causes": ["cause1"],
            "prevention": ["prevent1"],
            "safe_treatment": ["treat1"],
            "disclaimer": "Test disclaimer.",
            "is_uncertain": True,
        }
        with patch('utils.disease_knowledge.get_disease_info', return_value=mock_knowledge):
            resp = self._post("TestDisease")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["category"], "disease")
        self.assertIn("follow_up", data)
        self.assertIn("low", data["follow_up"].lower())

    def test_translation_fields_used(self):
        # Marathi translation for Tomato early blight is present in translations
        resp = self._post("Tomato___Early_blight", language="mr")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        knowledge = data["knowledge"]
        # display_name should be Marathi version
        self.assertEqual(knowledge["display_name"], "टॉमॅटो प्रारंभिक ब्लाइट")
        # description should be Marathi
        self.assertIn("टोमॅटो", knowledge["description"])

if __name__ == '__main__':
    unittest.main()
