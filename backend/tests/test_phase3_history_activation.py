import os
import io
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import jwt
from unittest.mock import patch, MagicMock

from backend.app import app as flask_app
from utils.auth_tokens import create_access_token


class FakeHistoryCursor:
    def __init__(self, rows=None, single_row=None):
        self.rows = rows or []
        self.single_row = single_row
        self.query = None
        self.params = None
        self.closed = False

    def execute(self, query, params=None):
        self.query = query
        self.params = params

    def fetchall(self):
        return self.rows

    def fetchone(self):
        if self.single_row is not None:
            return self.single_row
        return self.rows[0] if self.rows else None

    def close(self):
        self.closed = True


class FakeHistoryConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor
        self.closed = False

    def cursor(self, dictionary=False):
        return self.fake_cursor

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        self.closed = True


class Phase3DiagnosisHistoryActivationTests(unittest.TestCase):
    def setUp(self):
        self.client = flask_app.test_client()
        self.test_secret = "phase3-activation-test-secret-32-chars-long"
        self.env_patch = patch.dict(
            os.environ,
            {"JWT_SECRET_KEY": self.test_secret},
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def token_for(self, user_id, expired=False):
        now = datetime.now(timezone.utc)
        exp = now - timedelta(hours=1) if expired else now + timedelta(hours=12)
        payload = {"sub": str(user_id), "iat": now, "exp": exp}
        return jwt.encode(payload, self.test_secret, algorithm="HS256")

    def test_authenticated_history_retrieval(self):
        """Test that authenticated user receives enriched diagnosis history."""
        cursor = FakeHistoryCursor(rows=[{
            "id": 101,
            "predicted_class": "Tomato___Early_blight",
            "confidence": Decimal("94.50"),
            "notes": "Image-based model prediction",
            "diagnosis_date": datetime(2026, 10, 28, 10, 0, 0),
            "image_path": "leaf_1_abc123.jpg",
            "crop_id": 2,
            "disease_id": 31,
        }])
        conn = FakeHistoryConnection(cursor)

        with patch("routes.disease_routes.get_db_connection", return_value=conn):
            res = self.client.get(
                "/api/disease/history",
                headers={"Authorization": f"Bearer {self.token_for(1)}"}
            )
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data.get("status"), "success")
            self.assertEqual(data.get("count"), 1)
            item = data["history"][0]
            self.assertEqual(item["id"], 101)
            self.assertEqual(item["predicted_class"], "Tomato___Early_blight")
            self.assertEqual(item["confidence"], 94.50)
            self.assertEqual(item["crop_name"], "Tomato")
            self.assertIn("/api/disease/image/leaf_1_abc123.jpg", item["image_url"])
            self.assertIsInstance(item["symptoms"], list)
            self.assertIsInstance(item["safe_treatment"], list)

    def test_empty_history(self):
        """Test that user with no history receives an empty list cleanly."""
        cursor = FakeHistoryCursor(rows=[])
        conn = FakeHistoryConnection(cursor)

        with patch("routes.disease_routes.get_db_connection", return_value=conn):
            res = self.client.get(
                "/api/disease/history",
                headers={"Authorization": f"Bearer {self.token_for(42)}"}
            )
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data.get("status"), "success")
            self.assertEqual(data.get("count"), 0)
            self.assertEqual(data.get("history"), [])

    def test_invalid_token(self):
        """Test that request with bogus token returns 401."""
        res = self.client.get(
            "/api/disease/history",
            headers={"Authorization": "Bearer not.a.valid.jwt.token"}
        )
        self.assertEqual(res.status_code, 401)
        self.assertIn("error", res.get_json().get("status", ""))

    def test_expired_token(self):
        """Test that expired token returns 401."""
        expired_token = self.token_for(1, expired=True)
        res = self.client.get(
            "/api/disease/history",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        self.assertEqual(res.status_code, 401)
        self.assertIn("error", res.get_json().get("status", ""))

    def test_user_a_cannot_access_user_b_history(self):
        """Test user ownership isolation: query must filter strictly by token user_id."""
        cursor = FakeHistoryCursor(rows=[])
        conn = FakeHistoryConnection(cursor)

        with patch("routes.disease_routes.get_db_connection", return_value=conn):
            self.client.get(
                "/api/disease/history",
                headers={"Authorization": f"Bearer {self.token_for(55)}"}
            )
            # The database query MUST strictly specify user_id = %s with user 55
            self.assertIn("WHERE user_id = %s", cursor.query)
            self.assertEqual(cursor.params[0], 55)

    def test_history_detail_endpoint_access_granted(self):
        """Test that user can view details of their own diagnosis."""
        cursor = FakeHistoryCursor(single_row={
            "id": 88,
            "user_id": 10,
            "predicted_class": "Tomato___Late_blight",
            "confidence": Decimal("91.20"),
            "notes": "High humidity warning",
            "diagnosis_date": datetime(2026, 10, 27, 9, 30, 0),
            "image_path": "leaf_10_xyz.jpg",
            "crop_id": 1,
            "disease_id": 32,
        })
        conn = FakeHistoryConnection(cursor)

        with patch("routes.disease_routes.get_db_connection", return_value=conn):
            res = self.client.get(
                "/api/disease/history/88",
                headers={"Authorization": f"Bearer {self.token_for(10)}"}
            )
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data.get("status"), "success")
            self.assertEqual(data["detail"]["id"], 88)
            self.assertEqual(data["detail"]["predicted_class"], "Tomato___Late_blight")
            self.assertIn("symptoms", data["detail"])

    def test_history_detail_endpoint_access_denied_or_missing(self):
        """Test that accessing a non-existent or other user's record returns 404."""
        cursor = FakeHistoryCursor(single_row=None)
        conn = FakeHistoryConnection(cursor)

        with patch("routes.disease_routes.get_db_connection", return_value=conn):
            res = self.client.get(
                "/api/disease/history/999",
                headers={"Authorization": f"Bearer {self.token_for(10)}"}
            )
            self.assertEqual(res.status_code, 404)

    def test_image_path_traversal_prevented(self):
        """Test that path traversal attempts in image route are blocked."""
        res = self.client.get("/api/disease/image/..%2F..%2Fetc%2Fpasswd")
        self.assertIn(res.status_code, [400, 404])

    def test_image_ownership_security_blocks_unauthorized_user(self):
        """Test that User B cannot access User A's private leaf image."""
        cursor = FakeHistoryCursor(single_row={"user_id": 99})  # Belongs to user 99
        conn = FakeHistoryConnection(cursor)

        # Create a dummy image file in uploads
        uploads_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "uploads"
        )
        os.makedirs(uploads_dir, exist_ok=True)
        dummy_file = os.path.join(uploads_dir, "test_leaf_secure.jpg")
        with open(dummy_file, "wb") as f:
            f.write(b"fake image data")

        try:
            with patch("routes.disease_routes.get_db_connection", return_value=conn):
                # Request as User 50 (not user 99)
                res = self.client.get(
                    "/api/disease/image/test_leaf_secure.jpg",
                    headers={"Authorization": f"Bearer {self.token_for(50)}"}
                )
                self.assertEqual(res.status_code, 403)
        finally:
            if os.path.isfile(dummy_file):
                os.remove(dummy_file)

    def test_guest_prediction_remains_functional(self):
        """Test that guest leaf prediction still succeeds without auth header."""
        test_img_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "test_leaf.jpg"
        )
        if os.path.isfile(test_img_path):
            with open(test_img_path, "rb") as f:
                img_data = f.read()
            data = {
                "image": (io.BytesIO(img_data), "leaf.jpg")
            }
            res = self.client.post(
                "/api/disease/predict",
                data=data,
                content_type="multipart/form-data"
            )
            self.assertEqual(res.status_code, 200)
            res_data = res.get_json()
            self.assertEqual(res_data.get("status"), "success")
            self.assertFalse(res_data.get("history_saved"))


if __name__ == "__main__":
    unittest.main()
