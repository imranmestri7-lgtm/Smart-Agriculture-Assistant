import unittest
from utils.auth_tokens import create_access_token
from backend.app import app as flask_app

class Phase7LocalizationTests(unittest.TestCase):
    def setUp(self):
        self.client = flask_app.test_client()
        self.token = create_access_token(user_id=2)

    def _chat(self, msg, lang):
        return self.client.post(
            "/api/chat/message",
            json={"message": msg, "language": lang},
            headers={"Authorization": f"Bearer {self.token}"},
        )

    def test_knowledge_fields_present(self):
        # Generic query that triggers fallback knowledge entry
        resp = self._chat("Leaves have spots", "en")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        kn = data["knowledge"]
        # All required keys must exist (including disclaimer)
        required = {
            "class_name",
            "display_name",
            "crop",
            "description",
            "symptoms",
            "possible_causes",
            "prevention",
            "care_recommendations",
            "safe_treatment",
            "disclaimer",
        }
        self.assertTrue(required.issubset(set(kn.keys())))

    def test_invalid_language_fallback(self):
        resp = self._chat("What is irrigation?", "invalid")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        # Should fallback to English display name
        self.assertEqual(data["knowledge"]["display_name"], "Plant condition")

    def test_marathi_structure_and_content(self):
        msg = "टोमॅटोवरील रोगाबद्दल सांगा"
        resp = self._chat(msg, "mr")
        self.assertEqual(resp.status_code, 200)
        kn = resp.get_json()["knowledge"]
        # Verify that a translated disease entry is returned (Early blight)
        self.assertEqual(kn["display_name"], "टॉमॅटो प्रारंभिक ब्लाइट")
        # Ensure arrays are actually lists
        self.assertIsInstance(kn["symptoms"], list)
        self.assertIsInstance(kn["possible_causes"], list)
        self.assertIsInstance(kn["safe_treatment"], list)
        # Disclaimer must be a non‑empty string
        self.assertTrue(isinstance(kn["disclaimer"], str) and kn["disclaimer"].strip())
