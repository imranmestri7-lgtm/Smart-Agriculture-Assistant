import os
import unittest
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from backend.app import app as flask_app
from utils.auth_tokens import create_access_token


class FakeCursor:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.query = None
        self.params = None
        self.closed = False

    def execute(self, query, params=None):
        self.query = query
        self.params = params

    def fetchall(self):
        return self.rows

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor
        self.closed = False

    def cursor(self, dictionary=False):
        return self.fake_cursor

    def close(self):
        self.closed = True


class Phase3Tests(unittest.TestCase):
    def setUp(self):
        self.client = flask_app.test_client()
        self.env_patch = patch.dict(
            os.environ,
            {"JWT_SECRET_KEY": "phase3-test-secret-for-unit-tests"},
        )
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def token_for(self, user_id):
        return create_access_token(user_id)

    def test_history_requires_authentication(self):
        response = self.client.get("/api/disease/history")
        self.assertEqual(response.status_code, 401)

    def test_history_rejects_invalid_token(self):
        response = self.client.get(
            "/api/disease/history",
            headers={"Authorization": "Bearer invalid-token"},
        )
        self.assertEqual(response.status_code, 401)

    def test_history_returns_only_verified_users_records(self):
        cursor = FakeCursor(rows=[{
            "id": 7,
            "predicted_class": "Apple___Apple_scab",
            "confidence": Decimal("84.32"),
            "notes": "Image-based model prediction",
            "diagnosis_date": datetime(2026, 10, 25, 12, 30, 0),
        }])
        connection = FakeConnection(cursor)

        with patch(
            "routes.disease_routes.get_db_connection",
            return_value=connection,
        ):
            response = self.client.get(
                "/api/disease/history?limit=20",
                headers={
                    "Authorization": f"Bearer {self.token_for(123)}"
                },
            )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["history"][0]["id"], 7)
        self.assertEqual(data["history"][0]["confidence"], 84.32)

        # The SQL must filter records by the verified token's user ID.
        self.assertIn("WHERE user_id = %s", cursor.query)
        self.assertEqual(cursor.params, (123, 20))
        self.assertTrue(connection.closed)
        self.assertTrue(cursor.closed)

    def test_history_rejects_invalid_limit(self):
        response = self.client.get(
            "/api/disease/history?limit=abc",
            headers={
                "Authorization": f"Bearer {self.token_for(123)}"
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_history_handles_database_failure(self):
        with patch(
            "routes.disease_routes.get_db_connection",
            side_effect=RuntimeError("simulated database failure"),
        ):
            response = self.client.get(
                "/api/disease/history",
                headers={
                    "Authorization": f"Bearer {self.token_for(123)}"
                },
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["status"], "error")


if __name__ == "__main__":
    unittest.main()
