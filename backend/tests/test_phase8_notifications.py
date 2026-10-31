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


class MockNotificationsCursor:
    def __init__(self, notifications, preferences, crops, irrigations, diagnoses, farms):
        self.notifications = notifications
        self.preferences = preferences
        self.crops = crops
        self.irrigations = irrigations
        self.diagnoses = diagnoses
        self.farms = farms
        self.lastrowid = None
        self.rowcount = 0
        self._current_result = None

    def execute(self, query, params=None):
        clean_q = " ".join(query.split()).upper()
        params = list(params) if params else []

        # -------------------------------------------------------------
        # Preferences Query
        # -------------------------------------------------------------
        if "FROM NOTIFICATION_PREFERENCES WHERE USER_ID = %S" in clean_q:
            user_id = params[0]
            pref = self.preferences.get(user_id)
            if pref:
                self._current_result = [pref]
            else:
                self._current_result = []

        # -------------------------------------------------------------
        # Preferences Upsert
        # -------------------------------------------------------------
        elif "INSERT INTO NOTIFICATION_PREFERENCES" in clean_q:
            user_id = params[0]
            crop_rem = params[1]
            irrig_alt = params[2]
            weath_alt = params[3]
            dis_rem = params[4]
            self.preferences[user_id] = {
                "user_id": user_id,
                "crop_reminders": crop_rem,
                "irrigation_alerts": irrig_alt,
                "weather_alerts": weath_alt,
                "disease_reminders": dis_rem
            }
            self.rowcount = 1
            self._current_result = []

        # -------------------------------------------------------------
        # Check Existing by Unique Key
        # -------------------------------------------------------------
        elif "SELECT ID FROM NOTIFICATIONS WHERE USER_ID = %S AND UNIQUE_KEY = %S" in clean_q:
            user_id = params[0]
            ukey = params[1]
            found = [n for n in self.notifications if n["user_id"] == user_id and n.get("unique_key") == ukey]
            self._current_result = [{"id": found[0]["id"]}] if found else []

        # -------------------------------------------------------------
        # Insert Notification
        # -------------------------------------------------------------
        elif "INSERT INTO NOTIFICATIONS" in clean_q:
            # (user_id, category, title, message, severity, link, unique_key)
            new_id = (max([n["id"] for n in self.notifications], default=0)) + 1
            new_notif = {
                "id": new_id,
                "user_id": params[0],
                "category": params[1],
                "title": params[2],
                "message": params[3],
                "severity": params[4],
                "link": params[5],
                "unique_key": params[6],
                "is_read": 0,
                "created_at": datetime.now()
            }
            self.notifications.append(new_notif)
            self.lastrowid = new_id
            self.rowcount = 1
            self._current_result = []

        # -------------------------------------------------------------
        # Crops for Reminders
        # -------------------------------------------------------------
        elif "FROM CROPS C LEFT JOIN FARMS F ON F.ID = C.FARM_ID WHERE C.USER_ID = %S" in clean_q:
            user_id = params[0]
            farm_map = {f["id"]: f["farm_name"] for f in self.farms}
            res = []
            for c in self.crops:
                if c["user_id"] == user_id:
                    res.append({
                        "id": c["id"],
                        "crop_name": c.get("crop_name"),
                        "variety": c.get("variety"),
                        "planting_date": c.get("planting_date"),
                        "expected_harvest_date": c.get("expected_harvest_date"),
                        "growth_status": c.get("growth_status"),
                        "updated_at": c.get("updated_at"),
                        "farm_name": farm_map.get(c.get("farm_id"), "Farm")
                    })
            self._current_result = res

        elif "SELECT DISTINCT CROP_NAME FROM CROPS WHERE USER_ID = %S LIMIT 3" in clean_q:
            user_id = params[0]
            names = list({c["crop_name"] for c in self.crops if c["user_id"] == user_id and c.get("crop_name")})
            self._current_result = [{"crop_name": n} for n in names[:3]]

        # -------------------------------------------------------------
        # Irrigation for Alerts
        # -------------------------------------------------------------
        elif "FROM IRRIGATION_HISTORY WHERE USER_ID = %S ORDER BY CREATED_AT DESC" in clean_q:
            user_id = params[0]
            res = [i for i in self.irrigations if i["user_id"] == user_id]
            res.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
            self._current_result = res[:5]

        # -------------------------------------------------------------
        # Farms Location
        # -------------------------------------------------------------
        elif "SELECT LOCATION FROM FARMS WHERE USER_ID = %S AND LOCATION IS NOT NULL AND LOCATION != '' LIMIT 1" in clean_q:
            user_id = params[0]
            locs = [f["location"] for f in self.farms if f["user_id"] == user_id and f.get("location")]
            self._current_result = [{"location": locs[0]}] if locs else []

        elif "SELECT LOCATION FROM IRRIGATION_HISTORY WHERE USER_ID = %S AND LOCATION IS NOT NULL AND LOCATION != '' LIMIT 1" in clean_q:
            user_id = params[0]
            locs = [i["location"] for i in self.irrigations if i["user_id"] == user_id and i.get("location")]
            self._current_result = [{"location": locs[0]}] if locs else []

        # -------------------------------------------------------------
        # Diagnosis for Reminders
        # -------------------------------------------------------------
        elif "FROM DIAGNOSIS_HISTORY DH WHERE DH.USER_ID = %S ORDER BY DH.DIAGNOSIS_DATE DESC" in clean_q:
            user_id = params[0]
            res = [d for d in self.diagnoses if d["user_id"] == user_id]
            res.sort(key=lambda x: str(x.get("diagnosis_date") or ""), reverse=True)
            self._current_result = res[:5]

        # -------------------------------------------------------------
        # Unread Count
        # -------------------------------------------------------------
        elif "SELECT COUNT(*) AS CNT FROM NOTIFICATIONS WHERE USER_ID = %S AND IS_READ = 0" in clean_q:
            user_id = params[0]
            cnt = sum(1 for n in self.notifications if n["user_id"] == user_id and n.get("is_read") == 0)
            self._current_result = [{"cnt": cnt}]

        # -------------------------------------------------------------
        # Select Single Notification
        # -------------------------------------------------------------
        elif "SELECT ID FROM NOTIFICATIONS WHERE ID = %S AND USER_ID = %S" in clean_q:
            notif_id = params[0]
            user_id = params[1]
            found = [n for n in self.notifications if n["id"] == notif_id and n["user_id"] == user_id]
            self._current_result = [{"id": found[0]["id"]}] if found else []

        # -------------------------------------------------------------
        # Mark Single Read
        # -------------------------------------------------------------
        elif "UPDATE NOTIFICATIONS SET IS_READ = 1 WHERE ID = %S AND USER_ID = %S" in clean_q:
            notif_id = params[0]
            user_id = params[1]
            cnt = 0
            for n in self.notifications:
                if n["id"] == notif_id and n["user_id"] == user_id:
                    n["is_read"] = 1
                    cnt += 1
            self.rowcount = cnt
            self._current_result = []

        # -------------------------------------------------------------
        # Mark All Read
        # -------------------------------------------------------------
        elif "UPDATE NOTIFICATIONS SET IS_READ = 1 WHERE USER_ID = %S AND IS_READ = 0" in clean_q:
            user_id = params[0]
            cnt = 0
            for n in self.notifications:
                if n["user_id"] == user_id and n["is_read"] == 0:
                    n["is_read"] = 1
                    cnt += 1
            self.rowcount = cnt
            self._current_result = []

        # -------------------------------------------------------------
        # Delete Single Notification
        # -------------------------------------------------------------
        elif "DELETE FROM NOTIFICATIONS WHERE ID = %S AND USER_ID = %S" in clean_q:
            notif_id = params[0]
            user_id = params[1]
            before = len(self.notifications)
            self.notifications[:] = [n for n in self.notifications if not (n["id"] == notif_id and n["user_id"] == user_id)]
            self.rowcount = before - len(self.notifications)
            self._current_result = []

        # -------------------------------------------------------------
        # Clear All Notifications
        # -------------------------------------------------------------
        elif "DELETE FROM NOTIFICATIONS WHERE USER_ID = %S" in clean_q:
            user_id = params[0]
            before = len(self.notifications)
            self.notifications[:] = [n for n in self.notifications if n["user_id"] != user_id]
            self.rowcount = before - len(self.notifications)
            self._current_result = []

        # -------------------------------------------------------------
        # Select Notifications List
        # -------------------------------------------------------------
        elif "FROM NOTIFICATIONS" in clean_q and "SELECT" in clean_q:
            user_id = params[0]
            res = [n for n in self.notifications if n["user_id"] == user_id]
            if "IS_READ = 0" in clean_q:
                res = [n for n in res if n.get("is_read") == 0]
            if "CATEGORY = %S" in clean_q:
                cat = params[1] if len(params) > 1 and isinstance(params[1], str) else None
                if cat:
                    res = [n for n in res if n.get("category") == cat]
            res.sort(key=lambda x: (str(x.get("created_at") or ""), x["id"]), reverse=True)
            self._current_result = res

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


class MockNotificationsConnection:
    def __init__(self, notifications, preferences, crops, irrigations, diagnoses, farms):
        self.notifications = notifications
        self.preferences = preferences
        self.crops = crops
        self.irrigations = irrigations
        self.diagnoses = diagnoses
        self.farms = farms

    def cursor(self, dictionary=True):
        return MockNotificationsCursor(
            self.notifications, self.preferences, self.crops, self.irrigations, self.diagnoses, self.farms
        )

    def commit(self):
        pass

    def close(self):
        pass


class TestPhase8Notifications(unittest.TestCase):
    def setUp(self):
        self.client = flask_app.test_client()
        self.user1_id = 101
        self.user2_id = 102
        self.user1_token = create_access_token(self.user1_id)
        self.user2_token = create_access_token(self.user2_id)

        self.notifications_data = []
        self.preferences_data = {}
        self.farms_data = [
            {"id": 1, "user_id": 101, "farm_name": "Sahyadri Agro", "location": "Nashik, Maharashtra"},
            {"id": 2, "user_id": 102, "farm_name": "Deccan Farms", "location": "Pune, Maharashtra"}
        ]
        self.crops_data = [
            {
                "id": 1,
                "user_id": 101,
                "farm_id": 1,
                "crop_name": "Wheat",
                "variety": "Lokwan",
                "planting_date": date.today() - timedelta(days=90),
                "expected_harvest_date": date.today() + timedelta(days=3),  # Approaching harvest (3 days)
                "growth_status": "Ready for Harvest",
                "updated_at": datetime.now() - timedelta(days=5)
            },
            {
                "id": 2,
                "user_id": 101,
                "farm_id": 1,
                "crop_name": "Tomato",
                "variety": "Roma",
                "planting_date": date.today() - timedelta(days=40),
                "expected_harvest_date": date.today() + timedelta(days=40),
                "growth_status": "Flowering",
                "updated_at": datetime.now() - timedelta(days=35)  # Stale (> 30 days)
            }
        ]
        self.irrigations_data = [
            {
                "id": 1,
                "user_id": 101,
                "crop": "Wheat",
                "soil_moisture": 25.0,
                "is_irrigation_needed": 1,
                "water_quantity_mm": 30.0,
                "recommendation_status": "Irrigation Recommended",
                "created_at": datetime.now() - timedelta(hours=6)
            }
        ]
        self.diagnoses_data = [
            {
                "id": 1,
                "user_id": 101,
                "predicted_class": "Tomato___Early_blight",
                "confidence": 93.4,
                "diagnosis_date": datetime.now() - timedelta(days=2)
            }
        ]

    def _get_mock_conn(self):
        return MockNotificationsConnection(
            self.notifications_data, self.preferences_data, self.crops_data,
            self.irrigations_data, self.diagnoses_data, self.farms_data
        )

    # -------------------------------------------------------------
    # 1. AUTHENTICATION & ACCESS CONTROL
    # -------------------------------------------------------------
    def test_notifications_unauthorized_no_token(self):
        resp = self.client.get("/api/notifications")
        self.assertEqual(resp.status_code, 401)
        data = json.loads(resp.data)
        self.assertEqual(data["status"], "error")

    def test_notifications_unauthorized_invalid_token(self):
        resp = self.client.get("/api/notifications", headers={"Authorization": "Bearer invalid.jwt.token"})
        self.assertEqual(resp.status_code, 401)

    def test_unread_count_unauthorized(self):
        resp = self.client.get("/api/notifications/unread-count")
        self.assertEqual(resp.status_code, 401)

    def test_preferences_unauthorized(self):
        resp = self.client.get("/api/notifications/preferences")
        self.assertEqual(resp.status_code, 401)

        resp2 = self.client.put("/api/notifications/preferences", json={})
        self.assertEqual(resp2.status_code, 401)

    # -------------------------------------------------------------
    # 2. AUTO-GENERATION OF REMINDERS & ALERTS
    # -------------------------------------------------------------
    @patch("routes.notification_routes.get_db_connection")
    def test_generate_crop_reminders(self, mock_db):
        mock_db.return_value = self._get_mock_conn()

        resp = self.client.get(
            "/api/notifications",
            headers={"Authorization": f"Bearer {self.user1_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["status"], "success")

        notifs = data["notifications"]
        self.assertGreater(len(notifs), 0)

        categories = [n["category"] for n in notifs]
        self.assertIn("crop", categories)
        self.assertIn("irrigation", categories)
        self.assertIn("disease", categories)

        titles = [n["title"] for n in notifs]
        # Wheat approaching harvest reminder
        self.assertTrue(any("Harvest Approaching" in t or "Harvest Ready" in t for t in titles))
        # Tomato flowering stage care reminder
        self.assertTrue(any("Flowering" in t for t in titles))
        # Irrigation attention alert
        self.assertTrue(any("Irrigation" in t for t in titles))
        # Early blight prevention reminder
        self.assertTrue(any("Early Blight" in t for t in titles))

    # -------------------------------------------------------------
    # 3. DUPLICATE PREVENTION
    # -------------------------------------------------------------
    @patch("routes.notification_routes.get_db_connection")
    def test_no_duplicate_notifications_on_repeat(self, mock_db):
        conn = self._get_mock_conn()
        mock_db.return_value = conn

        # First request generates notifications
        resp1 = self.client.get(
            "/api/notifications",
            headers={"Authorization": f"Bearer {self.user1_token}"}
        )
        data1 = json.loads(resp1.data)
        count1 = len(data1["notifications"])

        # Second request must NOT duplicate notifications
        resp2 = self.client.get(
            "/api/notifications",
            headers={"Authorization": f"Bearer {self.user1_token}"}
        )
        data2 = json.loads(resp2.data)
        count2 = len(data2["notifications"])

        self.assertEqual(count1, count2)

    # -------------------------------------------------------------
    # 4. MARK READ / UNREAD & UNREAD COUNT
    # -------------------------------------------------------------
    @patch("routes.notification_routes.get_db_connection")
    def test_mark_single_read(self, mock_db):
        conn = self._get_mock_conn()
        mock_db.return_value = conn

        # Generate notifications first
        self.client.get("/api/notifications", headers={"Authorization": f"Bearer {self.user1_token}"})

        # Fetch notifications to get an ID
        notif = conn.notifications[0]
        notif_id = notif["id"]
        self.assertEqual(notif["is_read"], 0)

        # Mark as read
        resp = self.client.patch(
            f"/api/notifications/{notif_id}/read",
            headers={"Authorization": f"Bearer {self.user1_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["status"], "success")
        self.assertEqual(notif["is_read"], 1)

    @patch("routes.notification_routes.get_db_connection")
    def test_mark_all_read(self, mock_db):
        conn = self._get_mock_conn()
        mock_db.return_value = conn

        # Generate
        self.client.get("/api/notifications", headers={"Authorization": f"Bearer {self.user1_token}"})

        # Mark all read
        resp = self.client.patch(
            "/api/notifications/read-all",
            headers={"Authorization": f"Bearer {self.user1_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["unread_count"], 0)

        # Verify in memory
        for n in conn.notifications:
            if n["user_id"] == self.user1_id:
                self.assertEqual(n["is_read"], 1)

    # -------------------------------------------------------------
    # 5. DELETE & CLEAR NOTIFICATIONS
    # -------------------------------------------------------------
    @patch("routes.notification_routes.get_db_connection")
    def test_delete_individual_notification(self, mock_db):
        conn = self._get_mock_conn()
        mock_db.return_value = conn

        self.client.get("/api/notifications", headers={"Authorization": f"Bearer {self.user1_token}"})
        notif_id = conn.notifications[0]["id"]
        initial_len = len(conn.notifications)

        resp = self.client.delete(
            f"/api/notifications/{notif_id}",
            headers={"Authorization": f"Bearer {self.user1_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["status"], "success")
        self.assertEqual(len(conn.notifications), initial_len - 1)

    @patch("routes.notification_routes.get_db_connection")
    def test_clear_all_notifications(self, mock_db):
        conn = self._get_mock_conn()
        mock_db.return_value = conn

        self.client.get("/api/notifications", headers={"Authorization": f"Bearer {self.user1_token}"})
        self.assertGreater(len(conn.notifications), 0)

        resp = self.client.delete(
            "/api/notifications/clear",
            headers={"Authorization": f"Bearer {self.user1_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["status"], "success")

        user1_notifs = [n for n in conn.notifications if n["user_id"] == self.user1_id]
        self.assertEqual(len(user1_notifs), 0)

    # -------------------------------------------------------------
    # 6. NOTIFICATION PREFERENCES
    # -------------------------------------------------------------
    @patch("routes.notification_routes.get_db_connection")
    def test_get_and_update_preferences(self, mock_db):
        conn = self._get_mock_conn()
        mock_db.return_value = conn

        # GET defaults
        resp = self.client.get(
            "/api/notifications/preferences",
            headers={"Authorization": f"Bearer {self.user1_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        prefs = data["preferences"]
        self.assertTrue(prefs["crop_reminders"])
        self.assertTrue(prefs["irrigation_alerts"])

        # PUT update: disable irrigation_alerts
        resp2 = self.client.put(
            "/api/notifications/preferences",
            headers={"Authorization": f"Bearer {self.user1_token}"},
            json={
                "crop_reminders": True,
                "irrigation_alerts": False,
                "weather_alerts": True,
                "disease_reminders": True
            }
        )
        self.assertEqual(resp2.status_code, 200)
        data2 = json.loads(resp2.data)
        self.assertFalse(data2["preferences"]["irrigation_alerts"])

    # -------------------------------------------------------------
    # 7. FARMER DATA ISOLATION
    # -------------------------------------------------------------
    @patch("routes.notification_routes.get_db_connection")
    def test_farmer_data_isolation(self, mock_db):
        conn = self._get_mock_conn()
        mock_db.return_value = conn

        # Farmer 1 generates notifications
        self.client.get("/api/notifications", headers={"Authorization": f"Bearer {self.user1_token}"})
        user1_notif_id = conn.notifications[0]["id"]

        # Farmer 2 cannot mark farmer 1's notification as read
        resp = self.client.patch(
            f"/api/notifications/{user1_notif_id}/read",
            headers={"Authorization": f"Bearer {self.user2_token}"}
        )
        self.assertEqual(resp.status_code, 404)

        # Farmer 2 cannot delete farmer 1's notification
        resp2 = self.client.delete(
            f"/api/notifications/{user1_notif_id}",
            headers={"Authorization": f"Bearer {self.user2_token}"}
        )
        self.assertEqual(resp2.status_code, 404)


if __name__ == "__main__":
    unittest.main()
