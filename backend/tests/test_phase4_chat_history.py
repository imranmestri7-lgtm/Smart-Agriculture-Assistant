import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import jwt

from backend.app import app as flask_app


class FakeChatCursor:
    def __init__(self, rows=None, execute_exception=None):
        self.rows = rows if rows is not None else []
        self.execute_exception = execute_exception
        self.executed_queries = []
        self.closed = False

    def execute(self, query, params=None):
        if self.execute_exception:
            raise self.execute_exception
        self.executed_queries.append((query, params))

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def close(self):
        self.closed = True


class FakeChatConnection:
    def __init__(self, cursor):
        self.fake_cursor = cursor
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self, dictionary=False):
        return self.fake_cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


class Phase4ChatHistoryPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.client = flask_app.test_client()
        self.test_secret = "phase4-chat-test-secret-key-32-chars-long"
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

    def test_history_requires_token(self):
        """GET /api/chat/history requires Authorization header."""
        res = self.client.get("/api/chat/history")
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertIn("Authentication required", data["message"])

    def test_history_rejects_expired_token(self):
        """GET /api/chat/history rejects expired JWT."""
        token = self.token_for(101, expired=True)
        res = self.client.get(
            "/api/chat/history",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(res.status_code, 401)

    def test_history_rejects_invalid_limit(self):
        """GET /api/chat/history validates non-numeric limit."""
        token = self.token_for(101)
        res = self.client.get(
            "/api/chat/history?limit=abc",
            headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(res.status_code, 400)

    def test_history_empty_returns_empty_list(self):
        """GET /api/chat/history returns empty list when no conversations exist."""
        token = self.token_for(101)
        fake_cursor = FakeChatCursor(rows=[])
        fake_conn = FakeChatConnection(fake_cursor)

        with patch("routes.chat_routes.get_db_connection", return_value=fake_conn):
            res = self.client.get(
                "/api/chat/history",
                headers={"Authorization": f"Bearer {token}"}
            )

        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["history"], [])

    def test_history_returns_chronological_records_for_user(self):
        """GET /api/chat/history retrieves messages for user and presents them in chronological order."""
        token = self.token_for(101)
        # Mock descending query order from DB
        row2 = {
            "id": 2,
            "message": "What about watering?",
            "response": "Ensure soil moisture is maintained at 60-70%.",
            "created_at": datetime(2026, 10, 30, 11, 0, 0)
        }
        row1 = {
            "id": 1,
            "message": "Hello AgriSmart",
            "response": "Hello! How can I help your farm today?",
            "created_at": datetime(2026, 10, 30, 10, 0, 0)
        }
        # In DB, ordered by created_at DESC, id DESC: [row2, row1]
        fake_cursor = FakeChatCursor(rows=[row2, row1])
        fake_conn = FakeChatConnection(fake_cursor)

        with patch("routes.chat_routes.get_db_connection", return_value=fake_conn):
            res = self.client.get(
                "/api/chat/history",
                headers={"Authorization": f"Bearer {token}"}
            )

        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["count"], 2)
        # Endpoint reverses rows to chronological order: row1 then row2
        self.assertEqual(data["history"][0]["id"], 1)
        self.assertEqual(data["history"][0]["message"], "Hello AgriSmart")
        self.assertEqual(data["history"][1]["id"], 2)
        self.assertEqual(data["history"][1]["message"], "What about watering?")

        # Verify SQL query filtered by user_id
        query, params = fake_cursor.executed_queries[0]
        self.assertIn("user_id = %s", query)
        self.assertEqual(params[0], 101)

    def test_user_isolation(self):
        """User A only queries their own records; parameters use their token user_id."""
        token_a = self.token_for(42)
        fake_cursor_a = FakeChatCursor(rows=[])
        fake_conn_a = FakeChatConnection(fake_cursor_a)

        with patch("routes.chat_routes.get_db_connection", return_value=fake_conn_a):
            self.client.get(
                "/api/chat/history",
                headers={"Authorization": f"Bearer {token_a}"}
            )

        query_a, params_a = fake_cursor_a.executed_queries[0]
        self.assertEqual(params_a[0], 42)

        token_b = self.token_for(99)
        fake_cursor_b = FakeChatCursor(rows=[])
        fake_conn_b = FakeChatConnection(fake_cursor_b)

        with patch("routes.chat_routes.get_db_connection", return_value=fake_conn_b):
            self.client.get(
                "/api/chat/history",
                headers={"Authorization": f"Bearer {token_b}"}
            )

        query_b, params_b = fake_cursor_b.executed_queries[0]
        self.assertEqual(params_b[0], 99)

    def test_message_persistence_on_post(self):
        """POST /api/chat/message saves prompt and response into chat_history."""
        token = self.token_for(101)
        fake_cursor = FakeChatCursor()
        fake_conn = FakeChatConnection(fake_cursor)

        with patch("routes.chat_routes.get_db_connection", return_value=fake_conn):
            res = self.client.post(
                "/api/chat/message",
                headers={"Authorization": f"Bearer {token}"},
                json={"message": "How do I water tomato plants?", "language": "en"}
            )

        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(data.get("history_saved"))
        self.assertTrue(fake_conn.committed)

        # Check executed queries
        self.assertTrue(len(fake_cursor.executed_queries) >= 1)
        insert_query, insert_params = fake_cursor.executed_queries[0]
        self.assertIn("INSERT INTO chat_history", insert_query)
        self.assertEqual(insert_params[0], 101)
        self.assertEqual(insert_params[1], "How do I water tomato plants?")
        self.assertTrue(len(insert_params[2]) > 0)

    def test_clear_chat_history(self):
        """DELETE /api/chat/history clears conversations for authenticated user."""
        token = self.token_for(101)
        fake_cursor = FakeChatCursor()
        fake_conn = FakeChatConnection(fake_cursor)

        with patch("routes.chat_routes.get_db_connection", return_value=fake_conn):
            res = self.client.delete(
                "/api/chat/history",
                headers={"Authorization": f"Bearer {token}"}
            )

        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(fake_conn.committed)

        delete_query, delete_params = fake_cursor.executed_queries[0]
        self.assertIn("DELETE FROM chat_history", delete_query)
        self.assertEqual(delete_params, (101,))

    def test_history_database_error_handling(self):
        """GET /api/chat/history handles DB exceptions gracefully without crashing."""
        token = self.token_for(101)
        fake_cursor = FakeChatCursor(execute_exception=Exception("DB connection broken"))
        fake_conn = FakeChatConnection(fake_cursor)

        with patch("routes.chat_routes.get_db_connection", return_value=fake_conn):
            res = self.client.get(
                "/api/chat/history",
                headers={"Authorization": f"Bearer {token}"}
            )

        self.assertEqual(res.status_code, 500)
        data = res.get_json()
        self.assertEqual(data["status"], "error")


if __name__ == "__main__":
    unittest.main()
