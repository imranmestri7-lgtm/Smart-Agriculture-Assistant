import json
import os
import sys
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app import app as flask_app
from utils.auth_tokens import create_access_token


class MockChatCursor:
    def __init__(self, users_data, farms_data, crops_data, diagnoses_data, irrigations_data, chat_history_data):
        self.users = users_data
        self.farms = farms_data
        self.crops = crops_data
        self.diagnoses = diagnoses_data
        self.irrigations = irrigations_data
        self.chat_history = chat_history_data
        self.lastrowid = None
        self.rowcount = 0
        self._current_result = None

    def execute(self, query, params=None):
        clean_q = " ".join(query.split()).upper()
        params = list(params) if params else []

        # -------------------------------------------------------------
        # Farms
        # -------------------------------------------------------------
        if "FROM FARMS WHERE USER_ID = %S" in clean_q:
            user_id = params[0]
            res = [f for f in self.farms if f["user_id"] == user_id]
            self._current_result = res

        # -------------------------------------------------------------
        # Crops
        # -------------------------------------------------------------
        elif "FROM CROPS C LEFT JOIN FARMS F ON F.ID = C.FARM_ID WHERE C.USER_ID = %S" in clean_q:
            user_id = params[0]
            farm_map = {f["id"]: f["farm_name"] for f in self.farms}
            res = []
            for c in self.crops:
                if c["user_id"] == user_id:
                    res.append({
                        "id": c["id"],
                        "farm_id": c.get("farm_id"),
                        "crop_name": c.get("crop_name"),
                        "variety": c.get("variety"),
                        "planting_date": c.get("planting_date"),
                        "expected_harvest_date": c.get("expected_harvest_date"),
                        "growth_status": c.get("growth_status"),
                        "cultivated_area": c.get("cultivated_area"),
                        "area_unit": c.get("area_unit"),
                        "notes": c.get("notes"),
                        "updated_at": c.get("updated_at"),
                        "farm_name": farm_map.get(c.get("farm_id"), "Farm"),
                        "location": "Nashik, Maharashtra"
                    })
            self._current_result = res

        # -------------------------------------------------------------
        # Diagnoses
        # -------------------------------------------------------------
        elif "FROM DIAGNOSIS_HISTORY WHERE USER_ID = %S" in clean_q:
            user_id = params[0]
            res = [d for d in self.diagnoses if d["user_id"] == user_id]
            res.sort(key=lambda x: str(x.get("diagnosis_date") or ""), reverse=True)
            self._current_result = res

        # -------------------------------------------------------------
        # Irrigations
        # -------------------------------------------------------------
        elif "FROM IRRIGATION_HISTORY WHERE USER_ID = %S" in clean_q:
            user_id = params[0]
            res = [i for i in self.irrigations if i["user_id"] == user_id]
            res.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
            self._current_result = res

        # -------------------------------------------------------------
        # Chat History Insert
        # -------------------------------------------------------------
        elif "INSERT INTO CHAT_HISTORY" in clean_q:
            new_id = (max([c["id"] for c in self.chat_history], default=0)) + 1
            entry = {
                "id": new_id,
                "user_id": params[0],
                "message": params[1],
                "response": params[2],
                "created_at": datetime.now()
            }
            self.chat_history.append(entry)
            self.lastrowid = new_id
            self.rowcount = 1
            self._current_result = []

        # -------------------------------------------------------------
        # Chat History Select
        # -------------------------------------------------------------
        elif "FROM CHAT_HISTORY WHERE USER_ID = %S" in clean_q:
            user_id = params[0]
            res = [c for c in self.chat_history if c["user_id"] == user_id]
            res.sort(key=lambda x: (str(x.get("created_at") or ""), x["id"]), reverse=True)
            limit = params[1] if len(params) > 1 and isinstance(params[1], int) else 50
            self._current_result = res[:limit]

        # -------------------------------------------------------------
        # Chat History Delete
        # -------------------------------------------------------------
        elif "DELETE FROM CHAT_HISTORY WHERE USER_ID = %S" in clean_q:
            user_id = params[0]
            before = len(self.chat_history)
            self.chat_history[:] = [c for c in self.chat_history if c["user_id"] != user_id]
            self.rowcount = before - len(self.chat_history)
            self._current_result = []

        else:
            self._current_result = []

    def fetchall(self):
        return self._current_result or []

    def fetchone(self):
        if self._current_result:
            return self._current_result[0]
        return None

    def close(self):
        pass


class MockChatConnection:
    def __init__(self, users_data, farms_data, crops_data, diagnoses_data, irrigations_data, chat_history_data):
        self.users = users_data
        self.farms = farms_data
        self.crops = crops_data
        self.diagnoses = diagnoses_data
        self.irrigations = irrigations_data
        self.chat_history = chat_history_data

    def cursor(self, dictionary=True):
        return MockChatCursor(
            self.users, self.farms, self.crops, self.diagnoses, self.irrigations, self.chat_history
        )

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


class TestPhase9AdvancedAssistant(unittest.TestCase):
    def setUp(self):
        self.client = flask_app.test_client()
        self.user1_id = 101
        self.user2_id = 102
        self.user1_token = create_access_token(self.user1_id)
        self.user2_token = create_access_token(self.user2_id)

        self.users_data = [
            {"id": 101, "full_name": "Ramesh Patil", "email": "ramesh@example.com"},
            {"id": 102, "full_name": "Suresh More", "email": "suresh@example.com"}
        ]

        self.farms_data = [
            {
                "id": 1,
                "user_id": 101,
                "farm_name": "Sahyadri Agro",
                "location": "Nashik, Maharashtra",
                "total_area": 12.0,
                "area_unit": "acre"
            }
        ]

        self.crops_data = [
            {
                "id": 1,
                "user_id": 101,
                "farm_id": 1,
                "crop_name": "Wheat",
                "variety": "Lokwan",
                "planting_date": date.today() - timedelta(days=60),
                "expected_harvest_date": date.today() + timedelta(days=20),
                "growth_status": "Flowering",
                "cultivated_area": 5.0,
                "area_unit": "acre",
                "notes": "Field A, organic manure",
                "updated_at": datetime.now() - timedelta(days=2)
            },
            {
                "id": 2,
                "user_id": 101,
                "farm_id": 1,
                "crop_name": "Tomato",
                "variety": "Roma",
                "planting_date": date.today() - timedelta(days=85),
                "expected_harvest_date": date.today() + timedelta(days=5),
                "growth_status": "Ready for Harvest",
                "cultivated_area": 3.0,
                "area_unit": "acre",
                "notes": "Field B",
                "updated_at": datetime.now() - timedelta(days=1)
            }
        ]

        self.diagnoses_data = [
            {
                "id": 1,
                "user_id": 101,
                "predicted_class": "Tomato___Early_blight",
                "confidence": 92.5,
                "diagnosis_date": datetime.now() - timedelta(days=3)
            }
        ]

        self.irrigations_data = [
            {
                "id": 1,
                "user_id": 101,
                "crop": "Wheat",
                "soil_moisture": 32.0,
                "is_irrigation_needed": 1,
                "water_quantity_mm": 28.0,
                "recommendation_status": "Irrigation Recommended",
                "created_at": datetime.now() - timedelta(days=1)
            }
        ]

        self.chat_history_data = []

    def _get_mock_conn(self):
        return MockChatConnection(
            self.users_data, self.farms_data, self.crops_data,
            self.diagnoses_data, self.irrigations_data, self.chat_history_data
        )

    # -------------------------------------------------------------
    # 1. QUICK QUESTION SUGGESTIONS ENDPOINT
    # -------------------------------------------------------------
    def test_get_chat_suggestions_multilingual(self):
        # English
        resp_en = self.client.get("/api/chat/suggestions?language=en")
        self.assertEqual(resp_en.status_code, 200)
        data_en = json.loads(resp_en.data)
        self.assertEqual(data_en["language"], "en")
        labels_en = [s["label"] for s in data_en["suggestions"]]
        self.assertTrue(any("Crop status" in l or "crop status" in l for l in labels_en))

        # Marathi
        resp_mr = self.client.get("/api/chat/suggestions?language=mr")
        self.assertEqual(resp_mr.status_code, 200)
        data_mr = json.loads(resp_mr.data)
        self.assertEqual(data_mr["language"], "mr")

        # Hindi
        resp_hi = self.client.get("/api/chat/suggestions?language=hi")
        self.assertEqual(resp_hi.status_code, 200)
        data_hi = json.loads(resp_hi.data)
        self.assertEqual(data_hi["language"], "hi")

    # -------------------------------------------------------------
    # 2. CONTEXT-AWARE CROP STATUS INQUIRIES
    # -------------------------------------------------------------
    @patch("routes.chat_routes.get_db_connection")
    def test_crop_status_registered_crops(self, mock_db):
        mock_db.return_value = self._get_mock_conn()

        resp = self.client.post(
            "/api/chat/message",
            headers={"Authorization": f"Bearer {self.user1_token}"},
            json={"message": "What is my crop status?", "language": "en"}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["status"], "success")

        # Reply must accurately mention both Wheat and Tomato
        reply = data["reply"]
        self.assertIn("Wheat", reply)
        self.assertIn("Tomato", reply)
        self.assertIn("Flowering", reply)
        self.assertIn("Ready for Harvest", reply)

    @patch("routes.chat_routes.get_db_connection")
    def test_crop_status_empty_farmer(self, mock_db):
        empty_conn = MockChatConnection(self.users_data, [], [], [], [], [])
        mock_db.return_value = empty_conn

        resp = self.client.post(
            "/api/chat/message",
            headers={"Authorization": f"Bearer {self.user2_token}"},
            json={"message": "What crops am I growing?", "language": "en"}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        reply = data["reply"]
        # Must clearly state that no crops are registered without hallucinating
        self.assertIn("do not have any registered crops", reply.lower())

    # -------------------------------------------------------------
    # 3. SPECIFIC CROP CARE GUIDANCE
    # -------------------------------------------------------------
    @patch("routes.chat_routes.get_db_connection")
    def test_specific_crop_care_registered(self, mock_db):
        mock_db.return_value = self._get_mock_conn()

        resp = self.client.post(
            "/api/chat/message",
            headers={"Authorization": f"Bearer {self.user1_token}"},
            json={"message": "What should I do for my growing wheat crop?", "language": "en"}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        reply = data["reply"]

        # Wheat is in Flowering stage in user1's records
        self.assertIn("Wheat", reply)
        self.assertIn("Flowering", reply)

    @patch("routes.chat_routes.get_db_connection")
    def test_unregistered_crop_inquiry(self, mock_db):
        mock_db.return_value = self._get_mock_conn()

        resp = self.client.post(
            "/api/chat/message",
            headers={"Authorization": f"Bearer {self.user1_token}"},
            json={"message": "What should I do for my cotton crop?", "language": "en"}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        reply = data["reply"]

        # Informs farmer that Cotton is not registered under their farms
        self.assertIn("Cotton", reply)
        self.assertIn("not have", reply.lower())

    # -------------------------------------------------------------
    # 4. HARVEST REMINDERS & INQUIRIES
    # -------------------------------------------------------------
    @patch("routes.chat_routes.get_db_connection")
    def test_harvest_reminders(self, mock_db):
        mock_db.return_value = self._get_mock_conn()

        resp = self.client.post(
            "/api/chat/message",
            headers={"Authorization": f"Bearer {self.user1_token}"},
            json={"message": "Which crops are ready for harvest?", "language": "en"}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        reply = data["reply"]

        # Tomato is Ready for Harvest in user1's records
        self.assertIn("Tomato", reply)

    # -------------------------------------------------------------
    # 5. RECENT IRRIGATION RECOMMENDATIONS
    # -------------------------------------------------------------
    @patch("routes.chat_routes.get_db_connection")
    def test_recent_irrigation_recommendation(self, mock_db):
        mock_db.return_value = self._get_mock_conn()

        resp = self.client.post(
            "/api/chat/message",
            headers={"Authorization": f"Bearer {self.user1_token}"},
            json={"message": "What irrigation recommendation did I receive?", "language": "en"}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        reply = data["reply"]

        # Mentions 32% soil moisture and Wheat
        self.assertIn("Wheat", reply)
        self.assertIn("32", reply)

    # -------------------------------------------------------------
    # 6. RECENT DISEASE DIAGNOSIS & PRECAUTIONS
    # -------------------------------------------------------------
    @patch("routes.chat_routes.get_db_connection")
    def test_recent_disease_diagnosis(self, mock_db):
        mock_db.return_value = self._get_mock_conn()

        resp = self.client.post(
            "/api/chat/message",
            headers={"Authorization": f"Bearer {self.user1_token}"},
            json={"message": "Show my recent disease diagnosis", "language": "en"}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        reply = data["reply"]

        # Diagnosis record has Early blight
        self.assertTrue("Early blight" in reply or "Early Blight" in reply)
        # Includes non-diagnosis disclaimer
        self.assertIn("screening", reply.lower())

    # -------------------------------------------------------------
    # 7. FARM SUMMARY INQUIRY
    # -------------------------------------------------------------
    @patch("routes.chat_routes.get_db_connection")
    def test_farm_summary_inquiry(self, mock_db):
        mock_db.return_value = self._get_mock_conn()

        resp = self.client.post(
            "/api/chat/message",
            headers={"Authorization": f"Bearer {self.user1_token}"},
            json={"message": "Give me my farm summary", "language": "en"}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        reply = data["reply"]

        self.assertIn("Sahyadri Agro", reply)
        self.assertIn("Nashik", reply)

    # -------------------------------------------------------------
    # 8. FOLLOW-UP CONVERSATION CONTINUITY
    # -------------------------------------------------------------
    @patch("routes.chat_routes.get_db_connection")
    def test_follow_up_conversation_continuity(self, mock_db):
        conn = self._get_mock_conn()
        mock_db.return_value = conn

        # Turn 1: Discuss Wheat
        conn.chat_history.append({
            "id": 1,
            "user_id": self.user1_id,
            "message": "Tell me about my wheat crop",
            "response": "Your Wheat crop at Sahyadri Agro is in the Flowering stage.",
            "created_at": datetime.now() - timedelta(minutes=2)
        })

        # Turn 2: Follow-up question without naming "Wheat"
        resp = self.client.post(
            "/api/chat/message",
            headers={"Authorization": f"Bearer {self.user1_token}"},
            json={"message": "When will it be harvested?", "language": "en"}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        reply = data["reply"]

        # Should infer Wheat from the recent conversation turn
        self.assertIn("Wheat", reply)

    # -------------------------------------------------------------
    # 9. MULTILINGUAL RESPONSES (MARATHI & HINDI)
    # -------------------------------------------------------------
    @patch("routes.chat_routes.get_db_connection")
    def test_multilingual_context_responses(self, mock_db):
        mock_db.return_value = self._get_mock_conn()

        # Marathi
        resp_mr = self.client.post(
            "/api/chat/message",
            headers={"Authorization": f"Bearer {self.user1_token}"},
            json={"message": "माझ्या पिकांची स्थिती काय आहे?", "language": "mr"}
        )
        self.assertEqual(resp_mr.status_code, 200)
        data_mr = json.loads(resp_mr.data)
        self.assertIn("Wheat", data_mr["reply"])
        self.assertIn("Tomato", data_mr["reply"])
        self.assertIn("स्थिती", data_mr["reply"])

        # Hindi
        resp_hi = self.client.post(
            "/api/chat/message",
            headers={"Authorization": f"Bearer {self.user1_token}"},
            json={"message": "मेरी फसलों की स्थिति क्या है?", "language": "hi"}
        )
        self.assertEqual(resp_hi.status_code, 200)
        data_hi = json.loads(resp_hi.data)
        self.assertIn("Wheat", data_hi["reply"])
        self.assertIn("Tomato", data_hi["reply"])
        self.assertIn("स्थिति", data_hi["reply"])

    # -------------------------------------------------------------
    # 10. FARMER DATA ISOLATION
    # -------------------------------------------------------------
    @patch("routes.chat_routes.get_db_connection")
    def test_farmer_data_isolation(self, mock_db):
        mock_db.return_value = self._get_mock_conn()

        # Farmer 2 asks for crop status
        resp = self.client.post(
            "/api/chat/message",
            headers={"Authorization": f"Bearer {self.user2_token}"},
            json={"message": "Show my crops", "language": "en"}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        reply = data["reply"]

        # Farmer 2 has no crops in crops_data (only farmer 1 has crops)
        self.assertNotIn("Wheat", reply)
        self.assertNotIn("Tomato", reply)
        self.assertIn("not have any registered crops", reply.lower())


if __name__ == "__main__":
    unittest.main()
