import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from werkzeug.security import generate_password_hash
import jwt

from backend.app import app as flask_app
from utils.auth_tokens import create_access_token


class MockDBUserCursor:
    def __init__(self, users_db=None):
        self.users_db = users_db if users_db is not None else {}
        self.lastrowid = None
        self._current_result = None
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))
        clean_q = " ".join(query.split()).upper()

        if "SELECT ID FROM USERS WHERE EMAIL = %S" in clean_q:
            email = params[0].lower() if params else ""
            if email in self.users_db:
                self._current_result = [{"id": self.users_db[email]["id"]}]
            else:
                self._current_result = []

        elif "SELECT ID, FULL_NAME, MOBILE_NUMBER, EMAIL, PASSWORD_HASH, PREFERRED_LANGUAGE FROM USERS WHERE EMAIL = %S" in clean_q:
            email = params[0].lower() if params else ""
            if email in self.users_db:
                user = self.users_db[email]
                self._current_result = [{
                    "id": user["id"],
                    "full_name": user["full_name"],
                    "mobile_number": user.get("mobile_number"),
                    "email": user["email"],
                    "password_hash": user["password_hash"],
                    "preferred_language": user.get("preferred_language", "English")
                }]
            else:
                self._current_result = []

        elif "INSERT INTO USERS" in clean_q:
            # (full_name, email, password_hash, preferred_language)
            new_id = len(self.users_db) + 1
            self.lastrowid = new_id
            full_name = params[0]
            email = params[1].lower()
            pwd_hash = params[2]
            lang = params[3]
            self.users_db[email] = {
                "id": new_id,
                "full_name": full_name,
                "email": email,
                "password_hash": pwd_hash,
                "preferred_language": lang
            }
            self._current_result = []
        else:
            self._current_result = []

    def fetchone(self):
        if self._current_result:
            return self._current_result[0]
        return None

    def fetchall(self):
        return self._current_result or []

    def close(self):
        pass


class MockDBUserConnection:
    def __init__(self, cursor):
        self.mock_cursor = cursor
        self.committed = False
        self.rolled_back = False

    def cursor(self, dictionary=False):
        return self.mock_cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


class Phase5IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.client = flask_app.test_client()
        self.test_secret = "phase5-integration-test-secret-key-32-chars"
        self.env_patch = patch.dict(
            os.environ,
            {"JWT_SECRET_KEY": self.test_secret},
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

        # Prepopulate with a verified test user
        self.users_store = {
            "farmer@agrismart.com": {
                "id": 1,
                "full_name": "Ramesh Kumar",
                "email": "farmer@agrismart.com",
                "password_hash": generate_password_hash("SecretPass123"),
                "preferred_language": "Marathi"
            }
        }
        self.cursor = MockDBUserCursor(self.users_store)
        self.conn = MockDBUserConnection(self.cursor)

    def token_for(self, user_id):
        return create_access_token(user_id)

    # -------------------------------------------------------------------------
    # 1. Registration Flow Integration
    # -------------------------------------------------------------------------

    def test_registration_email_success(self):
        """Register a new farmer with valid details."""
        with patch("routes.auth_routes.get_db_connection", return_value=self.conn):
            res = self.client.post("/api/auth/register", json={
                "full_name": "Sita Patil",
                "auth_method": "email",
                "email": "sita@example.com",
                "password": "Password123",
                "confirm_password": "Password123",
                "preferred_language": "Marathi"
            })

        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["user"]["full_name"], "Sita Patil")
        self.assertEqual(data["user"]["preferred_language"], "Marathi")
        self.assertIn("sita@example.com", self.users_store)

    def test_registration_duplicate_email(self):
        """Reject registration when email is already registered."""
        with patch("routes.auth_routes.get_db_connection", return_value=self.conn):
            res = self.client.post("/api/auth/register", json={
                "full_name": "Duplicate Farmer",
                "auth_method": "email",
                "email": "farmer@agrismart.com",
                "password": "Password123",
                "confirm_password": "Password123"
            })

        self.assertEqual(res.status_code, 409)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertIn("already registered", data["message"].lower())

    def test_registration_validation_errors(self):
        """Reject invalid inputs during registration."""
        with patch("routes.auth_routes.get_db_connection", return_value=self.conn):
            # Short password
            res1 = self.client.post("/api/auth/register", json={
                "full_name": "Sita Patil",
                "auth_method": "email",
                "email": "test@test.com",
                "password": "123",
                "confirm_password": "123"
            })
            self.assertEqual(res1.status_code, 400)

            # Passwords mismatch
            res2 = self.client.post("/api/auth/register", json={
                "full_name": "Sita Patil",
                "auth_method": "email",
                "email": "test@test.com",
                "password": "Password123",
                "confirm_password": "MismatchPassword"
            })
            self.assertEqual(res2.status_code, 400)

    # -------------------------------------------------------------------------
    # 2. Login Flow Integration
    # -------------------------------------------------------------------------

    def test_login_success(self):
        """Authenticate user and return JWT token and user profile."""
        with patch("routes.auth_routes.get_db_connection", return_value=self.conn):
            res = self.client.post("/api/auth/login", json={
                "email": "farmer@agrismart.com",
                "password": "SecretPass123"
            })

        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(data.get("token"))
        self.assertEqual(data["user"]["full_name"], "Ramesh Kumar")
        self.assertEqual(data["user"]["preferred_language"], "Marathi")

    def test_login_invalid_credentials(self):
        """Reject login with incorrect password or non-existent email."""
        with patch("routes.auth_routes.get_db_connection", return_value=self.conn):
            # Wrong password
            res1 = self.client.post("/api/auth/login", json={
                "email": "farmer@agrismart.com",
                "password": "WrongPassword"
            })
            self.assertEqual(res1.status_code, 401)

            # Non-existent email
            res2 = self.client.post("/api/auth/login", json={
                "email": "unknown@agrismart.com",
                "password": "SecretPass123"
            })
            self.assertEqual(res2.status_code, 401)

    # -------------------------------------------------------------------------
    # 3. Protected Endpoints Authorization Enforcement
    # -------------------------------------------------------------------------

    def test_protected_endpoints_require_token(self):
        """Verify that protected API endpoints return 401 without Bearer token."""
        endpoints = [
            ("GET", "/api/chat/history"),
            ("DELETE", "/api/chat/history"),
            ("POST", "/api/chat/message"),
            ("GET", "/api/disease/history"),
            ("GET", "/api/irrigation/history"),
        ]

        for method, url in endpoints:
            if method == "GET":
                res = self.client.get(url)
            elif method == "DELETE":
                res = self.client.delete(url)
            elif method == "POST":
                res = self.client.post(url, json={"message": "test"})
            self.assertEqual(res.status_code, 401, f"{method} {url} did not enforce auth")

    # -------------------------------------------------------------------------
    # 4. Crop Recommendation Integration
    # -------------------------------------------------------------------------

    def test_crop_recommendation_flow(self):
        """Verify crop recommendation endpoint with valid and invalid values."""
        # Valid high nutrients -> Rice
        res1 = self.client.post("/api/crop/recommend", json={
            "nitrogen": 90,
            "phosphorus": 85,
            "potassium": 90
        })
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.get_json()["recommendation"], "Rice")

        # Valid low nutrients -> Wheat
        res2 = self.client.post("/api/crop/recommend", json={
            "nitrogen": 30,
            "phosphorus": 25,
            "potassium": 30
        })
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.get_json()["recommendation"], "Wheat")

        # Valid medium nutrients -> Maize
        res3 = self.client.post("/api/crop/recommend", json={
            "nitrogen": 60,
            "phosphorus": 50,
            "potassium": 55
        })
        self.assertEqual(res3.status_code, 200)
        self.assertEqual(res3.get_json()["recommendation"], "Maize")

    # -------------------------------------------------------------------------
    # 5. Multilingual Farmer Assistant Integration
    # -------------------------------------------------------------------------

    def test_multilingual_assistant_journey(self):
        """Send questions in English, Marathi, Hindi with token and receive localized responses."""
        token = self.token_for(1)
        headers = {"Authorization": f"Bearer {token}"}

        # Mock DB insertion for chat messages
        with patch("routes.chat_routes.get_db_connection", return_value=self.conn):
            # English
            res_en = self.client.post("/api/chat/message", json={
                "message": "How do I water my wheat crop?",
                "language": "en"
            }, headers=headers)
            self.assertEqual(res_en.status_code, 200)
            self.assertIn("irrigation", res_en.get_json()["category"])

            # Marathi
            res_mr = self.client.post("/api/chat/message", json={
                "message": "माझ्या पिकाला पाणी कसे द्यावे?",
                "language": "mr"
            }, headers=headers)
            self.assertEqual(res_mr.status_code, 200)
            self.assertTrue(res_mr.get_json()["reply"])

            # Hindi
            res_hi = self.client.post("/api/chat/message", json={
                "message": "फसल की सिंचाई कैसे करें?",
                "language": "hi"
            }, headers=headers)
            self.assertEqual(res_hi.status_code, 200)
            self.assertTrue(res_hi.get_json()["reply"])


if __name__ == "__main__":
    unittest.main()
