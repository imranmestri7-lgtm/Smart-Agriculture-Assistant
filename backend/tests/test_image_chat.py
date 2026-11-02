"""Tests for Farmer Assistant Image Upload & Camera Vision Feature."""

import io
import os
import unittest
from unittest.mock import MagicMock, patch
from PIL import Image

# Use backend test environment
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from utils.auth_tokens import create_access_token
from utils.image_chat import (
    analyze_leaf_image,
    save_chat_image,
    validate_image_file,
)


def _make_dummy_image_bytes(fmt="JPEG", size=(100, 100), color="green"):
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=fmt)
    buf.seek(0)
    return buf.getvalue()


class TestImageChatValidation(unittest.TestCase):
    """Test image file validation logic."""

    def test_valid_jpeg(self):
        img_bytes = _make_dummy_image_bytes("JPEG")
        mock_file = MagicMock()
        mock_file.filename = "leaf.jpg"
        mock_file.read.return_value = img_bytes

        data, err, code = validate_image_file(mock_file)
        self.assertIsNone(err)
        self.assertEqual(code, 200)
        self.assertEqual(data, img_bytes)

    def test_valid_png(self):
        img_bytes = _make_dummy_image_bytes("PNG")
        mock_file = MagicMock()
        mock_file.filename = "plant.png"
        mock_file.read.return_value = img_bytes

        data, err, code = validate_image_file(mock_file)
        self.assertIsNone(err)
        self.assertEqual(code, 200)

    def test_invalid_extension(self):
        mock_file = MagicMock()
        mock_file.filename = "document.pdf"

        data, err, code = validate_image_file(mock_file)
        self.assertIn("Invalid image format", err)
        self.assertEqual(code, 400)

    def test_empty_file(self):
        mock_file = MagicMock()
        mock_file.filename = "empty.jpg"
        mock_file.read.return_value = b""

        data, err, code = validate_image_file(mock_file)
        self.assertIn("empty", err)
        self.assertEqual(code, 400)

    def test_oversized_file(self):
        mock_file = MagicMock()
        mock_file.filename = "giant.jpg"
        # Over 5 MB (5 * 1024 * 1024 + 10 bytes)
        mock_file.read.return_value = b"x" * (5 * 1024 * 1024 + 10)

        data, err, code = validate_image_file(mock_file)
        self.assertIn("exceed 5 MB", err)
        self.assertEqual(code, 413)

    def test_corrupted_header(self):
        mock_file = MagicMock()
        mock_file.filename = "corrupted.jpg"
        mock_file.read.return_value = b"NOT_A_REAL_IMAGE_DATA_12345"

        data, err, code = validate_image_file(mock_file)
        self.assertIn("Corrupted or invalid", err)
        self.assertEqual(code, 400)


class TestImageChatEndpoints(unittest.TestCase):
    """Test authenticated endpoints for image chat and image serving."""

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.user1_id = 901
        self.user2_id = 902
        self.token_user1 = create_access_token(self.user1_id)
        self.token_user2 = create_access_token(self.user2_id)
        self.real_leaf_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "test_leaf.jpg"
        )

    def test_message_unauthenticated(self):
        img_bytes = _make_dummy_image_bytes()
        res = self.client.post(
            "/api/chat/message",
            data={
                "message": "What is this?",
                "image": (io.BytesIO(img_bytes), "leaf.jpg")
            },
            content_type="multipart/form-data"
        )
        self.assertEqual(res.status_code, 401)

    @patch("routes.chat_routes.get_db_connection")
    def test_image_message_success(self, mock_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value = mock_conn

        if os.path.exists(self.real_leaf_path):
            with open(self.real_leaf_path, "rb") as f:
                img_data = f.read()
        else:
            img_data = _make_dummy_image_bytes()

        res = self.client.post(
            "/api/chat/message",
            headers={"Authorization": f"Bearer {self.token_user1}"},
            data={
                "message": "Can you check my apple leaves?",
                "language": "en",
                "image": (io.BytesIO(img_data), "my_apple.jpg")
            },
            content_type="multipart/form-data"
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("image_url", data)
        self.assertTrue(data["image_url"].startswith("/api/chat/image/chat_leaf_901_"))
        self.assertIn("reply", data)
        self.assertIn("1. **What is Observed**:", data["reply"])
        self.assertIn("2. **Possible Plant Problem**:", data["reply"])
        self.assertIn("6. **When to Contact an Agricultural Expert**:", data["reply"])

    @patch("routes.chat_routes.get_db_connection")
    def test_image_message_default_prompt(self, mock_db):
        """When user provides no text with image, a localized default question is used."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value = mock_conn

        img_data = _make_dummy_image_bytes()
        res = self.client.post(
            "/api/chat/message",
            headers={"Authorization": f"Bearer {self.token_user1}"},
            data={
                "message": "",
                "language": "mr",
                "image": (io.BytesIO(img_data), "plant.png")
            },
            content_type="multipart/form-data"
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["language"], "mr")
        self.assertIn("image_url", data)

    @patch("routes.chat_routes.get_db_connection")
    def test_image_message_hindi(self, mock_db):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value = mock_conn

        img_data = _make_dummy_image_bytes()
        res = self.client.post(
            "/api/chat/message",
            headers={"Authorization": f"Bearer {self.token_user1}"},
            data={
                "message": "इस पौधे में क्या समस्या है?",
                "language": "hi",
                "image": (io.BytesIO(img_data), "crop.jpg")
            },
            content_type="multipart/form-data"
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["language"], "hi")
        self.assertIn("पौधे की तस्वीर", data["reply"])

    def test_get_image_isolation(self):
        """Farmer 901's image should not be accessible by Farmer 902."""
        img_bytes = _make_dummy_image_bytes()
        filename = save_chat_image(img_bytes, user_id=self.user1_id, original_filename="test.jpg")

        # Farmer 1 can access with header
        res1 = self.client.get(
            f"/api/chat/image/{filename}",
            headers={"Authorization": f"Bearer {self.token_user1}"}
        )
        self.assertEqual(res1.status_code, 200)

        # Farmer 1 can also access with ?token= query param for <img> rendering
        res1_query = self.client.get(f"/api/chat/image/{filename}?token={self.token_user1}")
        self.assertEqual(res1_query.status_code, 200)

        # Unauthenticated request fails with 401
        res_unauth = self.client.get(f"/api/chat/image/{filename}")
        self.assertEqual(res_unauth.status_code, 401)

        # Farmer 2 access fails with 403 Forbidden
        res2 = self.client.get(
            f"/api/chat/image/{filename}",
            headers={"Authorization": f"Bearer {self.token_user2}"}
        )
        self.assertEqual(res2.status_code, 403)

    def test_get_image_path_traversal(self):
        res = self.client.get(
            "/api/chat/image/..%2F..%2Fconfig.py",
            headers={"Authorization": f"Bearer {self.token_user1}"}
        )
        self.assertIn(res.status_code, (400, 404))

    @patch("routes.chat_routes.get_db_connection")
    def test_chat_history_with_image(self, mock_db):
        """History should parse and expose image_url."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                "id": 1,
                "message": "[image:/api/chat/image/chat_leaf_901_test.jpg] What is this disease?",
                "response": "Observation: Apple Scab.",
                "created_at": None
            }
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value = mock_conn

        res = self.client.get(
            "/api/chat/history",
            headers={"Authorization": f"Bearer {self.token_user1}"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["count"], 1)
        item = data["history"][0]
        self.assertEqual(item["image_url"], "/api/chat/image/chat_leaf_901_test.jpg")
        self.assertEqual(item["clean_message"], "What is this disease?")


if __name__ == "__main__":
    unittest.main()
