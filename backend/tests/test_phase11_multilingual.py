"""Unit tests for Phase 11: Complete Multilingual Support.

Tests:
1. Language normalization and resolution logic (en, mr, hi).
2. Backend message dictionary translations across en, mr, and hi.
3. PUT /api/auth/preferred-language endpoint and authentication guards.
4. GET /api/auth/profile preference persistence.
5. Multilingual chatbot responses and language header prioritization.
6. Localized disease guidance and recommendations endpoint.
"""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app import app as flask_app
from utils.auth_tokens import create_access_token
from utils.i18n import (
    MESSAGES,
    get_request_language,
    normalize_language,
    t_backend,
)


class Phase11MultilingualUtilsTests(unittest.TestCase):
    """Test suite for backend/utils/i18n.py functions."""

    def test_normalize_language(self):
        self.assertEqual(normalize_language("en"), "en")
        self.assertEqual(normalize_language("English"), "en")
        self.assertEqual(normalize_language("ENGLISH"), "en")
        self.assertEqual(normalize_language("mr"), "mr")
        self.assertEqual(normalize_language("Marathi"), "mr")
        self.assertEqual(normalize_language("mr-IN"), "mr")
        self.assertEqual(normalize_language("hi"), "hi")
        self.assertEqual(normalize_language("Hindi"), "hi")
        self.assertEqual(normalize_language("hi-IN"), "hi")
        self.assertEqual(normalize_language(""), "en")
        self.assertEqual(normalize_language(None), "en")
        self.assertEqual(normalize_language("french"), "en")

    def test_t_backend_localization(self):
        # English
        self.assertEqual(t_backend("login_success", lang="en"), "Login successful")
        self.assertEqual(t_backend("crop_required", lang="en"), "Crop name is required")

        # Marathi
        self.assertEqual(t_backend("login_success", lang="mr"), "लॉगिन यशस्वी झाले")
        self.assertEqual(t_backend("crop_required", lang="mr"), "पिकाचे नाव आवश्यक आहे")

        # Hindi
        self.assertEqual(t_backend("login_success", lang="hi"), "लॉगिन सफल रहा")
        self.assertEqual(t_backend("crop_required", lang="hi"), "फसल का नाम आवश्यक है")

        # Missing key fallback
        self.assertEqual(t_backend("nonexistent_key", lang="mr", default="Default Val"), "Default Val")

    def test_messages_dictionary_completeness(self):
        # Verify that all en keys exist in mr and hi
        en_keys = set(MESSAGES["en"].keys())
        mr_keys = set(MESSAGES["mr"].keys())
        hi_keys = set(MESSAGES["hi"].keys())

        missing_mr = en_keys - mr_keys
        missing_hi = en_keys - hi_keys

        self.assertEqual(len(missing_mr), 0, f"Missing Marathi keys: {missing_mr}")
        self.assertEqual(len(missing_hi), 0, f"Missing Hindi keys: {missing_hi}")


class Phase11EndpointsTests(unittest.TestCase):
    """Test suite for Phase 11 API endpoints and multilingual integrations."""

    def setUp(self):
        self.client = flask_app.test_client()
        self.user_id = 999
        self.token = create_access_token(user_id=self.user_id)

    def test_get_request_language_resolution(self):
        with flask_app.test_request_context("/api/test", headers={"X-Language": "mr"}):
            self.assertEqual(get_request_language(), "mr")

        with flask_app.test_request_context("/api/test", headers={"X-Language": "hi"}):
            self.assertEqual(get_request_language(), "hi")

        with flask_app.test_request_context("/api/test?lang=mr"):
            self.assertEqual(get_request_language(), "mr")

        with flask_app.test_request_context("/api/test", json={"language": "hi"}):
            self.assertEqual(get_request_language(), "hi")

        with flask_app.test_request_context("/api/test", headers={"Accept-Language": "mr-IN,mr;q=0.9"}):
            self.assertEqual(get_request_language(), "mr")

        with flask_app.test_request_context("/api/test"):
            self.assertEqual(get_request_language(), "en")

    def test_update_preferred_language_unauthorized(self):
        resp = self.client.put("/api/auth/preferred-language", json={"preferred_language": "mr"})
        self.assertEqual(resp.status_code, 401)

    def test_update_preferred_language_missing_body(self):
        resp = self.client.put(
            "/api/auth/preferred-language",
            headers={"Authorization": f"Bearer {self.token}"},
            json={},
        )
        self.assertEqual(resp.status_code, 400)

    @patch("routes.auth_routes.get_db_connection")
    def test_update_preferred_language_marathi(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        resp = self.client.put(
            "/api/auth/preferred-language",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"preferred_language": "mr"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["preferred_language"], "Marathi")
        self.assertEqual(data["lang_code"], "mr")
        self.assertIn("अद्यतनित", data["message"])
        mock_conn.commit.assert_called_once()

    @patch("routes.auth_routes.get_db_connection")
    def test_update_preferred_language_hindi(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        resp = self.client.put(
            "/api/auth/preferred-language",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"preferred_language": "hi"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["preferred_language"], "Hindi")
        self.assertEqual(data["lang_code"], "hi")
        self.assertIn("अपडेट", data["message"])
        mock_conn.commit.assert_called_once()

    @patch("routes.auth_routes.get_db_connection")
    def test_get_user_profile_with_preferred_language(self, mock_get_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "id": self.user_id,
            "full_name": "Ramesh Patil",
            "email": "ramesh@example.com",
            "mobile_number": "9876543210",
            "preferred_language": "Marathi",
        }
        mock_get_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        resp = self.client.get(
            "/api/auth/profile",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["user"]["preferred_language"], "Marathi")

    def test_disease_recommendations_multilingual(self):
        # 1. English
        resp_en = self.client.post(
            "/api/disease/recommend",
            headers={"X-Language": "en"},
            json={
                "prediction": {"class_name": "Tomato___Early_blight", "confidence": 85.5},
                "answers": {"plant": "Tomato", "symptoms": "Brown or black spots"},
            },
        )
        self.assertEqual(resp_en.status_code, 200)
        data_en = resp_en.get_json()
        self.assertEqual(data_en["status"], "success")
        self.assertIn("Take clear photos", data_en["recommendations"][0])
        self.assertIn("general precautionary suggestions", data_en["disclaimer"])

        # 2. Marathi
        resp_mr = self.client.post(
            "/api/disease/recommend",
            headers={"X-Language": "mr"},
            json={
                "prediction": {"class_name": "Tomato___Early_blight", "confidence": 85.5},
                "answers": {"plant": "Tomato", "symptoms": "Brown or black spots"},
            },
        )
        self.assertEqual(resp_mr.status_code, 200)
        data_mr = resp_mr.get_json()
        self.assertEqual(data_mr["status"], "success")
        self.assertIn("फोटो काढा", data_mr["recommendations"][0])
        self.assertIn("सावधगिरीच्या सूचना", data_mr["disclaimer"])

        # 3. Hindi
        resp_hi = self.client.post(
            "/api/disease/recommend",
            headers={"X-Language": "hi"},
            json={
                "prediction": {"class_name": "Tomato___Early_blight", "confidence": 85.5},
                "answers": {"plant": "Tomato", "symptoms": "Brown or black spots"},
            },
        )
        self.assertEqual(resp_hi.status_code, 200)
        data_hi = resp_hi.get_json()
        self.assertEqual(data_hi["status"], "success")
        self.assertIn("तस्वीरें लें", data_hi["recommendations"][0])
        self.assertIn("एहतियाती सुझाव", data_hi["disclaimer"])

    def test_chatbot_multilingual_parity(self):
        # 1. Marathi query
        resp_mr = self.client.post(
            "/api/chat/message",
            headers={
                "Authorization": f"Bearer {self.token}",
                "X-Language": "mr",
            },
            json={
                "message": "पाणी कधी द्यावे?",
                "language": "mr",
            },
        )
        self.assertEqual(resp_mr.status_code, 200)
        data_mr = resp_mr.get_json()
        self.assertEqual(data_mr["status"], "success")
        self.assertEqual(data_mr["language"], "mr")
        # Ensure Marathi characters exist in reply
        has_devanagari = any("\u0900" <= ch <= "\u097f" for ch in data_mr["reply"])
        self.assertTrue(has_devanagari, "Response should be in Devanagari script")

        # 2. Hindi query
        resp_hi = self.client.post(
            "/api/chat/message",
            headers={
                "Authorization": f"Bearer {self.token}",
                "X-Language": "hi",
            },
            json={
                "message": "सिंचाई कब करनी चाहिए?",
                "language": "hi",
            },
        )
        self.assertEqual(resp_hi.status_code, 200)
        data_hi = resp_hi.get_json()
        self.assertEqual(data_hi["status"], "success")
        self.assertEqual(data_hi["language"], "hi")
        has_devanagari_hi = any("\u0900" <= ch <= "\u097f" for ch in data_hi["reply"])
        self.assertTrue(has_devanagari_hi, "Response should be in Devanagari script")


if __name__ == "__main__":
    unittest.main()
