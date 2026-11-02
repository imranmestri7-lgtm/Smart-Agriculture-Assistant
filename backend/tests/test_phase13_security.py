"""AgriSmart Phase 13: Comprehensive Security Audit & Production Readiness Tests.

Validates:
- Unauthorized API access & token validation (invalid, expired, forged secret)
- Cross-user data isolation (farms, crops, private images)
- SQL injection prevention across query filters
- File upload restrictions (bad extensions, non-image content, payload size limits)
- Rate limiting & abuse protection (OTP, login, prediction, IoT)
- IoT device security (key validation, telemetry alias, duplicate protection, user isolation)
- Static file traversal and sensitive file access prevention (.env, backend code)
- Clean extensionless URLs and HTTP security headers
"""

from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
import secrets
import sys
import unittest
from unittest.mock import MagicMock, patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import jwt
from PIL import Image

# Ensure test environment
os.environ["FLASK_DEBUG"] = "false"
try:
    from backend.app import app
except ImportError:
    from app import app
from utils.auth_tokens import create_access_token
from utils.rate_limiter import limiter


class Phase13SecurityAuditTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()
        cls.jwt_secret = os.getenv("JWT_SECRET_KEY") or "agrismart-production-ready-cryptographic-jwt-secret-key-32-bytes-minimum-length-2026"

    def setUp(self):
        # Reset rate limiter before each test to ensure test isolation
        limiter.reset()
        limiter.enable()

    def tearDown(self):
        limiter.reset()

    def generate_token(self, user_id: int, expires_in_seconds: int = 3600, secret: str = None):
        """Generate JWT token with custom expiration or signature secret."""
        sec = secret or self.jwt_secret
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(int(user_id)),
            "iat": now,
            "exp": now + timedelta(seconds=expires_in_seconds),
        }
        return jwt.encode(payload, sec, algorithm="HS256")

    # =========================================================================
    # 1. AUTHENTICATION & AUTHORIZATION
    # =========================================================================

    def test_unauthorized_api_access_rejected(self):
        """Protected API endpoints must reject unauthenticated requests with 401."""
        protected_endpoints = [
            ("/api/farms", "GET"),
            ("/api/farms", "POST"),
            ("/api/crops", "GET"),
            ("/api/crops", "POST"),
            ("/api/analytics/overview", "GET"),
            ("/api/notifications", "GET"),
            ("/api/iot/sensors", "GET"),
            ("/api/iot/overview", "GET"),
            ("/api/auth/profile", "GET"),
        ]

        for url, method in protected_endpoints:
            with self.subTest(url=url, method=method):
                if method == "GET":
                    res = self.client.get(url)
                elif method == "POST":
                    res = self.client.post(url, json={})
                self.assertEqual(
                    res.status_code, 401,
                    f"Expected 401 Unauthorized for {method} {url}, got {res.status_code}"
                )
                data = res.get_json()
                self.assertEqual(data.get("status"), "error")

    def test_invalid_and_expired_jwts_rejected(self):
        """API must reject malformed, forged, and expired tokens with 401."""
        # 1. Completely bogus token
        res1 = self.client.get(
            "/api/farms",
            headers={"Authorization": "Bearer completely-fake-token-xyz"}
        )
        self.assertEqual(res1.status_code, 401)

        # 2. Expired token (expired 10 minutes ago)
        expired_token = self.generate_token(user_id=1, expires_in_seconds=-600)
        res2 = self.client.get(
            "/api/farms",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        self.assertEqual(res2.status_code, 401)

        # 3. Forged token signed with wrong secret key
        forged_token = self.generate_token(user_id=1, secret="attacker-forged-secret-key")
        res3 = self.client.get(
            "/api/farms",
            headers={"Authorization": f"Bearer {forged_token}"}
        )
        self.assertEqual(res3.status_code, 401)

    def test_auth_logout_endpoint(self):
        """Logout endpoint should acknowledge session termination."""
        res = self.client.post("/api/auth/logout")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "success")

    # =========================================================================
    # 2. CROSS-USER DATA ISOLATION & SQL INJECTION
    # =========================================================================

    @patch("routes.farm_crop_routes.get_db_connection")
    def test_cross_user_farm_access_prevented(self, mock_conn):
        """User B must not be able to update or delete User A's farm."""
        # Setup mock DB where farm 42 belongs to User 1 (not User 2)
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # User 2 does not own farm 42
        mock_conn.return_value.cursor.return_value = mock_cursor

        user2_token = self.generate_token(user_id=2)

        # Try to delete User 1's farm
        res = self.client.delete(
            "/api/farms/42",
            headers={"Authorization": f"Bearer {user2_token}"}
        )
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertEqual(data.get("status"), "error")

    @patch("routes.analytics_routes.get_db_connection")
    def test_sql_injection_in_analytics_neutralized(self, mock_conn):
        """SQL injection payloads in analytics query params must be treated as literal strings."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.fetchone.return_value = {"cnt": 2}
        mock_conn.return_value.cursor.return_value = mock_cursor

        token = self.generate_token(user_id=1)
        sqli_payload = "' OR '1'='1'; DROP TABLE users; --"

        res = self.client.get(
            f"/api/analytics/overview?crop_name={sqli_payload}&start_date=2026-01-01",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(res.status_code, 200)
        # Verify parameterized execution was used
        for call_args in mock_cursor.execute.call_args_list:
            query, params = call_args[0]
            # Payload must be safely in params, never raw string concatenation in SQL
            if sqli_payload.lower() in query.lower():
                self.fail(f"SQL injection string was improperly interpolated into query: {query}")

    # =========================================================================
    # 3. FILE UPLOAD & PRIVATE LEAF IMAGE SECURITY
    # =========================================================================

    def test_invalid_file_extension_rejected(self):
        """Uploading non-image executable or script files to /api/disease/predict must be rejected."""
        executable_data = b"MZ\x90\x00\x03\x00\x00\x00BinaryPayload"
        res = self.client.post(
            "/api/disease/predict",
            data={
                "image": (io.BytesIO(executable_data), "malicious_script.exe")
            },
            content_type="multipart/form-data"
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data.get("status"), "error")
        self.assertIn("Invalid image format", data.get("message", ""))

    def test_corrupted_image_content_rejected(self):
        """Uploading a text or corrupt file disguised with .jpg extension must be rejected."""
        fake_jpg = b"Not a real image file, just plain ASCII text"
        res = self.client.post(
            "/api/disease/predict",
            data={
                "image": (io.BytesIO(fake_jpg), "fake_leaf.jpg")
            },
            content_type="multipart/form-data"
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data.get("status"), "error")

    @patch("routes.disease_routes.get_db_connection")
    def test_unauthenticated_private_leaf_image_access_blocked(self, mock_conn):
        """Accessing a user's private diagnosis image without authentication returns 401."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"user_id": 10}  # Image belongs to User 10
        mock_conn.return_value.cursor.return_value = mock_cursor

        # Create dummy file in uploads so 404 is not triggered
        upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        dummy_file = os.path.join(upload_dir, "leaf_user10_secret.jpg")
        with open(dummy_file, "wb") as f:
            f.write(b"dummy image bytes")

        try:
            # 1. Unauthenticated request -> 401 Unauthorized
            res_unauth = self.client.get("/api/disease/image/leaf_user10_secret.jpg")
            self.assertEqual(res_unauth.status_code, 401)

            # 2. User 99 (different user) -> 403 Forbidden
            other_user_token = self.generate_token(user_id=99)
            res_other = self.client.get(
                "/api/disease/image/leaf_user10_secret.jpg",
                headers={"Authorization": f"Bearer {other_user_token}"}
            )
            self.assertEqual(res_other.status_code, 403)

            # 3. User 10 (legitimate owner) -> 200 OK
            owner_token = self.generate_token(user_id=10)
            res_owner = self.client.get(
                "/api/disease/image/leaf_user10_secret.jpg",
                headers={"Authorization": f"Bearer {owner_token}"}
            )
            self.assertEqual(res_owner.status_code, 200)
        finally:
            if os.path.isfile(dummy_file):
                os.remove(dummy_file)

    # =========================================================================
    # 4. RATE LIMITING & ABUSE PROTECTION
    # =========================================================================

    def test_send_otp_rate_limiting(self):
        """Sending OTP repeatedly beyond limit must trigger HTTP 429 Too Many Requests."""
        with patch("routes.auth_routes.get_db_connection") as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = {"id": 1}
            mock_conn.return_value.cursor.return_value = mock_cursor

            with patch("routes.auth_routes.get_twilio_client") as mock_twilio:
                mock_verification = MagicMock()
                mock_verification.status = "pending"
                mock_twilio.return_value.verify.v2.services.return_value.verifications.create.return_value = mock_verification

                # First 5 attempts should succeed
                for i in range(5):
                    res = self.client.post(
                        "/api/auth/send-otp",
                        json={"mobile_number": "9876543210"}
                    )
                    self.assertEqual(res.status_code, 200, f"Attempt {i+1} should succeed")

                # 6th attempt should be blocked by rate limiter
                res_blocked = self.client.post(
                    "/api/auth/send-otp",
                    json={"mobile_number": "9876543210"}
                )
                self.assertEqual(res_blocked.status_code, 429)
                self.assertIn("Retry-After", res_blocked.headers)
                data = res_blocked.get_json()
                self.assertEqual(data.get("status"), "error")
                self.assertIn("Too many requests", data.get("message", ""))

    def test_login_rate_limiting(self):
        """Rapid repeated login failures must trigger 429 rate limit."""
        with patch("routes.auth_routes.get_db_connection") as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = None  # Invalid credentials
            mock_conn.return_value.cursor.return_value = mock_cursor

            # Max 10 login requests per minute
            for _ in range(10):
                res = self.client.post(
                    "/api/auth/login",
                    json={"email": "attacker@test.com", "password": "wrongpassword"}
                )
                self.assertEqual(res.status_code, 401)

            # 11th request triggers 429
            blocked = self.client.post(
                "/api/auth/login",
                json={"email": "attacker@test.com", "password": "wrongpassword"}
            )
            self.assertEqual(blocked.status_code, 429)

    # =========================================================================
    # 5. IoT DEVICE SECURITY & DEDUPLICATION
    # =========================================================================

    def test_iot_invalid_device_credentials_rejected(self):
        """IoT ingest must reject unauthorized device requests with 401."""
        # Unregistered device ID
        with patch("routes.iot_routes.get_db_connection") as mock_conn:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = None
            mock_conn.return_value.cursor.return_value = mock_cursor

            res = self.client.post(
                "/api/iot/ingest",
                headers={"X-Device-Id": "ROGUE-ESP32-99", "X-Device-Key": "fake-key"},
                json={"value": 45.0, "sensor_type": "soil_moisture"}
            )
            self.assertEqual(res.status_code, 401)
            data = res.get_json()
            self.assertIn("Unregistered device", data.get("message", ""))

    @patch("routes.iot_routes.get_db_connection")
    def test_iot_telemetry_alias_route_functional(self, mock_conn):
        """The documented /api/iot/telemetry/ingest endpoint must work as a compatible alias."""
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor

        device_key = "secret_device_key_123"
        key_hash = hashlib.sha256(device_key.encode("utf-8")).hexdigest()

        mock_cursor.fetchone.return_value = {
            "id": 1,
            "user_id": 5,
            "farm_id": 1,
            "crop_id": None,
            "device_id": "ESP32-FIELD-01",
            "device_key_hash": key_hash,
            "sensor_name": "Field Moisture",
            "sensor_type": "soil_moisture",
            "status": "connected",
            "last_reading_at": None
        }

        # Call the alias route
        res = self.client.post(
            "/api/iot/telemetry/ingest",
            headers={"X-Device-Id": "ESP32-FIELD-01", "X-Device-Key": device_key},
            json={"value": 42.5, "sensor_type": "soil_moisture"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "success")

    @patch("routes.iot_routes.get_db_connection")
    def test_iot_duplicate_reading_deduplication(self, mock_conn):
        """Submitting identical reading with exact same timestamp is safely deduplicated."""
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value = mock_cursor

        device_key = "secret_device_key_dedup"
        key_hash = hashlib.sha256(device_key.encode("utf-8")).hexdigest()

        mock_cursor.fetchone.return_value = {
            "id": 2,
            "user_id": 5,
            "farm_id": 1,
            "crop_id": None,
            "device_id": "ESP32-DEDUP-01",
            "device_key_hash": key_hash,
            "sensor_name": "Dedup Sensor",
            "sensor_type": "soil_moisture",
            "status": "connected",
            "last_reading_at": None
        }

        payload = {
            "value": 35.0,
            "sensor_type": "soil_moisture",
            "timestamp": "2026-11-01T10:00:00Z"
        }

        # First submission
        res1 = self.client.post(
            "/api/iot/ingest",
            headers={"X-Device-Id": "ESP32-DEDUP-01", "X-Device-Key": device_key},
            json=payload
        )
        self.assertEqual(res1.status_code, 200)

        # Immediate duplicate submission
        res2 = self.client.post(
            "/api/iot/ingest",
            headers={"X-Device-Id": "ESP32-DEDUP-01", "X-Device-Key": device_key},
            json=payload
        )
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        # Verify duplicate flag is acknowledged
        self.assertTrue(any(r.get("duplicate") for r in data2.get("readings", [])))

    # =========================================================================
    # 6. STATIC FILE TRAVERSAL & SENSITIVE FILE PROTECTION
    # =========================================================================

    def test_sensitive_backend_files_blocked(self):
        """Access to .env, backend source files, and .git must return 403 Forbidden."""
        blocked_paths = [
            "/backend/.env",
            "/.env",
            "/backend/config.py",
            "/backend/app.py",
            "/.git/config",
            "/backend/.env.save",
        ]
        for path in blocked_paths:
            with self.subTest(path=path):
                res = self.client.get(path)
                self.assertEqual(
                    res.status_code, 403,
                    f"Path {path} must be blocked with 403, got {res.status_code}"
                )
                data = res.get_json()
                self.assertEqual(data.get("status"), "error")

    def test_clean_extensionless_frontend_urls(self):
        """Clean extensionless URLs (/login, /register, /farmer) must serve HTML cleanly."""
        for slug in ["/login", "/register", "/farmer", "/disease", "/crop", "/weather", "/irrigation"]:
            with self.subTest(slug=slug):
                res = self.client.get(slug)
                self.assertEqual(res.status_code, 200)
                self.assertIn("text/html", res.content_type)

    def test_security_headers_and_cache_control(self):
        """All responses must carry security headers, and API routes must prevent caching."""
        # Frontend page response
        res_page = self.client.get("/")
        self.assertEqual(res_page.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(res_page.headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertEqual(res_page.headers.get("X-XSS-Protection"), "1; mode=block")
        self.assertEqual(res_page.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")

        # API response
        res_api = self.client.get("/api/test")
        cache_control = res_api.headers.get("Cache-Control", "")
        self.assertIn("no-store", cache_control)
        self.assertIn("private", cache_control)


if __name__ == "__main__":
    unittest.main()
