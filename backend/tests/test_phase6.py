import os
import unittest
from utils.auth_tokens import create_access_token
from backend.app import app as flask_app

class Phase6Tests(unittest.TestCase):
    def setUp(self):
        self.client = flask_app.test_client()
        # create a valid JWT using the secret in .env
        self.token = create_access_token(user_id=1)

    def _post(self, message, language=None):
        payload = {"message": message}
        if language is not None:
            payload["language"] = language
        return self.client.post(
            "/api/chat/message",
            json=payload,
            headers={"Authorization": f"Bearer {self.token}"},
        )

    def test_english_fallback_auto(self):
        resp = self._post("What is irrigation?")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("reply", data)
        self.assertIn("knowledge", data)
        # English fallback should give English display name (from base KB)
        self.assertEqual(data["knowledge"]["display_name"], "Plant condition")

    def test_marathi_translation(self):
        # Marathi query about tomato early blight
        msg = "टोमॅटोच्या पानांवर काळे डाग आहेत, काय करावे?"
        resp = self._post(msg, language="mr")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        kn = data["knowledge"]
        self.assertEqual(kn["display_name"], "टॉमॅटो प्रारंभिक ब्लाइट")
        self.assertIn("ही मॉडेलवर आधारित माहिती आहे", kn["disclaimer"])

    def test_hindi_translation(self):
        msg = "टमाटर के पत्तों पर काले धब्बे हैं, क्या करें?"
        resp = self._post(msg, language="hi")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        kn = data["knowledge"]
        self.assertEqual(kn["display_name"], "टमाटर प्रारम्भिक ब्लाइट")
        self.assertIn("यह मॉडल पर आधारित जानकारी है", kn["disclaimer"])

    def test_missing_translation_fallback(self):
        # Apple Scab has no Marathi/Hindi translation in the file
        msg = "Apple scab symptoms"
        resp = self._post(msg, language="mr")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        kn = data["knowledge"]
        self.assertEqual(kn["display_name"], "Apple Scab")
        # disclaimer should be the English one from the base KB
        self.assertIn("This evaluation is a model‑assisted prediction", kn["disclaimer"])

    def test_invalid_language_defaults_to_english(self):
        resp = self._post("What is weather?", language="xx")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["knowledge"]["display_name"], "Plant condition")
