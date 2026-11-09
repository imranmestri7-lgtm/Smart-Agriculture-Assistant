import json
import os
import sys
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import patch, MagicMock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app import app as flask_app
from utils.auth_tokens import create_access_token


class MockSmartNotifCursor:
    def __init__(self, notifications, preferences, crops, irrigations, diagnoses, farms, push_subs):
        self.notifications = notifications
        self.preferences = preferences
        self.crops = crops
        self.irrigations = irrigations
        self.diagnoses = diagnoses
        self.farms = farms
        self.push_subs = push_subs
        self.lastrowid = None
        self.rowcount = 0
        self._current_result = None

    def execute(self, query, params=None):
        clean_q = " ".join(query.split()).upper()
        params = list(params) if params else []

        # Preferences Query
        if "FROM NOTIFICATION_PREFERENCES WHERE USER_ID = %S" in clean_q:
            uid = int(params[0])
            pref = self.preferences.get(uid)
            self._current_result = [pref] if pref else []

        # Preferences Upsert
        elif "INSERT INTO NOTIFICATION_PREFERENCES" in clean_q:
            uid = int(params[0])
            self.preferences[uid] = {
                "user_id": uid,
                "crop_reminders": params[1],
                "irrigation_alerts": params[2],
                "weather_alerts": params[3],
                "disease_reminders": params[4],
                "push_enabled": params[5] if len(params) > 5 else 0
            }
            self.rowcount = 1
            self._current_result = []

        # Check existing notification by unique key
        elif "SELECT ID FROM NOTIFICATIONS WHERE USER_ID = %S AND UNIQUE_KEY = %S" in clean_q:
            uid = int(params[0])
            ukey = params[1]
            found = [n for n in self.notifications if int(n["user_id"]) == uid and n.get("unique_key") == ukey]
            self._current_result = [{"id": found[0]["id"]}] if found else []

        # Insert notification
        elif "INSERT INTO NOTIFICATIONS" in clean_q:
            new_id = (max([n["id"] for n in self.notifications], default=0)) + 1
            # (user_id, category, title, message, severity, link, unique_key, related_id)
            new_notif = {
                "id": new_id,
                "user_id": int(params[0]),
                "category": params[1],
                "title": params[2],
                "message": params[3],
                "severity": params[4],
                "link": params[5],
                "unique_key": params[6] if len(params) > 6 else None,
                "related_id": params[7] if len(params) > 7 else None,
                "is_read": 0,
                "created_at": datetime.now()
            }
            self.notifications.append(new_notif)
            self.lastrowid = new_id
            self.rowcount = 1
            self._current_result = []

        # Crops query
        elif "FROM CROPS C LEFT JOIN FARMS F ON F.ID = C.FARM_ID WHERE C.USER_ID = %S" in clean_q:
            uid = int(params[0])
            farm_map = {f["id"]: f.get("farm_name", "Farm") for f in self.farms}
            res = []
            for c in self.crops:
                if int(c["user_id"]) == uid:
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
            uid = int(params[0])
            names = list({c["crop_name"] for c in self.crops if int(c["user_id"]) == uid and c.get("crop_name")})
            self._current_result = [{"crop_name": n} for n in names[:3]]

        # Irrigation query
        elif "FROM IRRIGATION_HISTORY WHERE USER_ID = %S ORDER BY CREATED_AT DESC" in clean_q:
            uid = int(params[0])
            res = [i for i in self.irrigations if int(i["user_id"]) == uid]
            res.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
            self._current_result = res[:5]

        # Farm location query
        elif "SELECT LOCATION FROM FARMS WHERE USER_ID = %S AND LOCATION IS NOT NULL AND LOCATION != '' LIMIT 1" in clean_q:
            uid = int(params[0])
            locs = [f["location"] for f in self.farms if int(f["user_id"]) == uid and f.get("location")]
            self._current_result = [{"location": locs[0]}] if locs else []

        elif "SELECT LOCATION FROM IRRIGATION_HISTORY WHERE USER_ID = %S AND LOCATION IS NOT NULL AND LOCATION != '' LIMIT 1" in clean_q:
            uid = int(params[0])
            locs = [i["location"] for i in self.irrigations if int(i["user_id"]) == uid and i.get("location")]
            self._current_result = [{"location": locs[0]}] if locs else []

        # Diagnosis query
        elif "FROM DIAGNOSIS_HISTORY DH WHERE DH.USER_ID = %S ORDER BY DH.DIAGNOSIS_DATE DESC" in clean_q:
            uid = int(params[0])
            res = [d for d in self.diagnoses if int(d["user_id"]) == uid]
            res.sort(key=lambda x: str(x.get("diagnosis_date") or ""), reverse=True)
            self._current_result = res[:5]

        # Push subscription queries
        elif "SELECT COUNT(*) AS CNT FROM PUSH_SUBSCRIPTIONS WHERE USER_ID = %S" in clean_q:
            uid = int(params[0])
            cnt = sum(1 for s in self.push_subs if int(s["user_id"]) == uid)
            self._current_result = [{"cnt": cnt}]

        elif "FROM PUSH_SUBSCRIPTIONS WHERE USER_ID = %S" in clean_q and "SELECT" in clean_q:
            uid = int(params[0])
            res = [s for s in self.push_subs if int(s["user_id"]) == uid]
            self._current_result = res

        elif "INSERT INTO PUSH_SUBSCRIPTIONS" in clean_q:
            uid = int(params[0])
            endpoint = params[1]
            existing = [s for s in self.push_subs if int(s["user_id"]) == uid and s["endpoint"] == endpoint]
            if existing:
                existing[0]["p256dh"] = params[2]
                existing[0]["auth"] = params[3]
                existing[0]["user_agent"] = params[4]
                existing[0]["updated_at"] = datetime.now()
            else:
                self.push_subs.append({
                    "id": len(self.push_subs) + 1,
                    "user_id": uid,
                    "endpoint": endpoint,
                    "p256dh": params[2],
                    "auth": params[3],
                    "user_agent": params[4],
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                })
            self.rowcount = 1
            self._current_result = []

        elif "DELETE FROM PUSH_SUBSCRIPTIONS WHERE USER_ID = %S" in clean_q:
            uid = int(params[0])
            endpoint = params[1] if len(params) > 1 else None
            before = len(self.push_subs)
            if endpoint:
                self.push_subs[:] = [s for s in self.push_subs if not (int(s["user_id"]) == uid and s["endpoint"] == endpoint)]
            else:
                self.push_subs[:] = [s for s in self.push_subs if int(s["user_id"]) != uid]
            self.rowcount = before - len(self.push_subs)
            self._current_result = []

        # Unread count
        elif "SELECT COUNT(*) AS CNT FROM NOTIFICATIONS WHERE USER_ID = %S AND IS_READ = 0" in clean_q:
            uid = int(params[0])
            cnt = sum(1 for n in self.notifications if int(n["user_id"]) == uid and n.get("is_read") == 0)
            self._current_result = [{"cnt": cnt}]

        # Single notification select
        elif "SELECT ID FROM NOTIFICATIONS WHERE ID = %S AND USER_ID = %S" in clean_q:
            notif_id = int(params[0])
            uid = int(params[1])
            found = [n for n in self.notifications if n["id"] == notif_id and int(n["user_id"]) == uid]
            self._current_result = [{"id": found[0]["id"]}] if found else []

        # Mark single read
        elif "UPDATE NOTIFICATIONS SET IS_READ = 1 WHERE ID = %S AND USER_ID = %S" in clean_q:
            notif_id = int(params[0])
            uid = int(params[1])
            for n in self.notifications:
                if n["id"] == notif_id and int(n["user_id"]) == uid:
                    n["is_read"] = 1
            self.rowcount = 1
            self._current_result = []

        # Mark single unread
        elif "UPDATE NOTIFICATIONS SET IS_READ = 0 WHERE ID = %S AND USER_ID = %S" in clean_q:
            notif_id = int(params[0])
            uid = int(params[1])
            for n in self.notifications:
                if n["id"] == notif_id and int(n["user_id"]) == uid:
                    n["is_read"] = 0
            self.rowcount = 1
            self._current_result = []

        # Mark all read
        elif "UPDATE NOTIFICATIONS SET IS_READ = 1 WHERE USER_ID = %S AND IS_READ = 0" in clean_q:
            uid = int(params[0])
            for n in self.notifications:
                if int(n["user_id"]) == uid and n["is_read"] == 0:
                    n["is_read"] = 1
            self.rowcount = 1
            self._current_result = []

        # Delete single notification
        elif "DELETE FROM NOTIFICATIONS WHERE ID = %S AND USER_ID = %S" in clean_q:
            notif_id = int(params[0])
            uid = int(params[1])
            before = len(self.notifications)
            self.notifications[:] = [n for n in self.notifications if not (n["id"] == notif_id and int(n["user_id"]) == uid)]
            self.rowcount = before - len(self.notifications)
            self._current_result = []

        # Clear all notifications
        elif "DELETE FROM NOTIFICATIONS WHERE USER_ID = %S" in clean_q:
            uid = int(params[0])
            self.notifications[:] = [n for n in self.notifications if int(n["user_id"]) != uid]
            self.rowcount = 1
            self._current_result = []

        # Select notifications list
        elif "FROM NOTIFICATIONS" in clean_q and "SELECT" in clean_q:
            uid = int(params[0])
            res = [n for n in self.notifications if int(n["user_id"]) == uid]
            if "IS_READ = 0" in clean_q:
                res = [n for n in res if n.get("is_read") == 0]
            elif "IS_READ = 1" in clean_q:
                res = [n for n in res if n.get("is_read") == 1]
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


class MockSmartNotifConnection:
    def __init__(self, notifications, preferences, crops, irrigations, diagnoses, farms, push_subs):
        self.notifications = notifications
        self.preferences = preferences
        self.crops = crops
        self.irrigations = irrigations
        self.diagnoses = diagnoses
        self.farms = farms
        self.push_subs = push_subs

    def cursor(self, dictionary=True):
        return MockSmartNotifCursor(
            self.notifications, self.preferences, self.crops, self.irrigations,
            self.diagnoses, self.farms, self.push_subs
        )

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


class SmartNotificationsUpgradeTestCase(unittest.TestCase):
    def setUp(self):
        os.environ["WEATHER_API_KEY"] = "mock-key-for-test"
        self.client = flask_app.test_client()
        self.farmer1_id = 101
        self.farmer2_id = 202

        self.farmer1_token = create_access_token(self.farmer1_id)
        self.farmer2_token = create_access_token(self.farmer2_id)

        self.notifications = []
        self.preferences = {}
        self.crops = []
        self.irrigations = []
        self.diagnoses = []
        self.farms = [{"id": 1, "user_id": self.farmer1_id, "farm_name": "Sunrise Farm", "location": "Pune"}]
        self.push_subs = []

    def _get_mock_conn(self):
        return MockSmartNotifConnection(
            self.notifications, self.preferences, self.crops, self.irrigations,
            self.diagnoses, self.farms, self.push_subs
        )

    @patch("routes.notification_routes.requests.get")
    @patch("routes.notification_routes.get_db_connection")
    def test_smart_weather_alerts_generation(self, mock_db, mock_req):
        """Verify Weather alerts trigger on heavy rain, high temp, strong wind and evaporation review"""
        mock_db.return_value = self._get_mock_conn()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {
            "location": {"name": "Pune", "region": "Maharashtra"},
            "current": {
                "temp_c": 39.5,
                "wind_kph": 42.0,
                "humidity": 20,
                "condition": {"text": "Hot & Windy"}
            },
            "forecast": {
                "forecastday": [{
                    "date": str(date.today()),
                    "day": {
                        "totalprecip_mm": 32.5,
                        "daily_chance_of_rain": 85,
                        "maxtemp_c": 40.0,
                        "maxwind_kph": 42.0
                    }
                }]
            }
        }
        mock_req.return_value = mock_response

        res = self.client.post(
            "/api/notifications/generate",
            headers={"Authorization": f"Bearer {self.farmer1_token}"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")

        weather_alerts = [n for n in self.notifications if n["category"] == "weather" and int(n["user_id"]) == self.farmer1_id]
        self.assertTrue(len(weather_alerts) >= 2, f"Expected multiple weather alerts, got: {len(weather_alerts)}")

        # Check heavy rain alert
        rain_alerts = [n for n in weather_alerts if "Rain" in n["title"]]
        self.assertTrue(len(rain_alerts) > 0)
        self.assertEqual(rain_alerts[0]["severity"], "warning")

        # Check heat alert
        heat_alerts = [n for n in weather_alerts if "Temperature" in n["title"] or "Heat" in n["title"]]
        self.assertTrue(len(heat_alerts) > 0)
        self.assertEqual(heat_alerts[0]["severity"], "warning")

    @patch("routes.notification_routes.requests.get")
    @patch("routes.notification_routes.get_db_connection")
    def test_smart_irrigation_alerts_generation(self, mock_db, mock_req):
        """Verify Smart Irrigation alerts trigger for rain postponement with water saved, deficit, and tactile check"""
        mock_db.return_value = self._get_mock_conn()
        mock_req.side_effect = Exception("No external weather")

        self.irrigations.append({
            "id": 501,
            "user_id": self.farmer1_id,
            "crop": "Wheat",
            "soil_type": "Clay",
            "growth_stage": "Flowering",
            "soil_moisture": 25.0,
            "recommendation_status": "Postpone for rain",
            "water_quantity_mm": 0.0,
            "water_saved_mm": 25.0,
            "is_irrigation_needed": 0,
            "created_at": datetime.now()
        })

        res = self.client.post(
            "/api/notifications/generate",
            headers={"Authorization": f"Bearer {self.farmer1_token}"}
        )
        self.assertEqual(res.status_code, 200)

        irrig_alerts = [n for n in self.notifications if n["category"] == "irrigation" and int(n["user_id"]) == self.farmer1_id]
        self.assertTrue(len(irrig_alerts) >= 1)
        postpone_alerts = [n for n in irrig_alerts if "Postponed" in n["title"]]
        self.assertTrue(len(postpone_alerts) > 0)
        self.assertIn("L/ha", postpone_alerts[0]["message"])

    @patch("routes.notification_routes.requests.get")
    @patch("routes.notification_routes.get_db_connection")
    def test_plant_disease_alerts_generation(self, mock_db, mock_req):
        """Verify Disease diagnosis generates alert linked with related_id and disease history"""
        mock_db.return_value = self._get_mock_conn()
        mock_req.side_effect = Exception("No weather")

        self.diagnoses.append({
            "id": 901,
            "user_id": self.farmer1_id,
            "predicted_class": "Tomato___Early_blight",
            "confidence": 94.5,
            "diagnosis_date": datetime.now()
        })

        res = self.client.post(
            "/api/notifications/generate",
            headers={"Authorization": f"Bearer {self.farmer1_token}"}
        )
        self.assertEqual(res.status_code, 200)

        disease_alerts = [n for n in self.notifications if n["category"] == "disease" and int(n["user_id"]) == self.farmer1_id]
        self.assertEqual(len(disease_alerts), 1)
        self.assertIn("Early Blight", disease_alerts[0]["title"])
        self.assertEqual(disease_alerts[0]["related_id"], 901)
        self.assertIn("disease.html#diagnosisHistorySection", disease_alerts[0]["link"])

    @patch("routes.notification_routes.get_db_connection")
    def test_filter_tabs_read_unread_all(self, mock_db):
        """Verify notifications can be queried by read_status: all, unread, read"""
        mock_db.return_value = self._get_mock_conn()

        self.notifications.append({
            "id": 1, "user_id": self.farmer1_id, "category": "crop", "title": "Harvest Ready",
            "message": "Crop is ready", "severity": "info", "is_read": 0, "created_at": datetime.now()
        })
        self.notifications.append({
            "id": 2, "user_id": self.farmer1_id, "category": "weather", "title": "Weather Clear",
            "message": "Clear skies", "severity": "info", "is_read": 1, "created_at": datetime.now()
        })

        # Query unread only
        res_unread = self.client.get(
            "/api/notifications?read_status=unread",
            headers={"Authorization": f"Bearer {self.farmer1_token}"}
        )
        data_unread = res_unread.get_json()
        self.assertEqual(data_unread["status"], "success")
        self.assertEqual(len(data_unread["notifications"]), 1)
        self.assertEqual(data_unread["notifications"][0]["id"], 1)

        # Query read only
        res_read = self.client.get(
            "/api/notifications?read_status=read",
            headers={"Authorization": f"Bearer {self.farmer1_token}"}
        )
        data_read = res_read.get_json()
        self.assertEqual(data_read["status"], "success")
        self.assertEqual(len(data_read["notifications"]), 1)
        self.assertEqual(data_read["notifications"][0]["id"], 2)

        # Query all
        res_all = self.client.get(
            "/api/notifications?read_status=all",
            headers={"Authorization": f"Bearer {self.farmer1_token}"}
        )
        data_all = res_all.get_json()
        self.assertEqual(len(data_all["notifications"]), 2)

    @patch("routes.notification_routes.get_db_connection")
    def test_mark_single_unread_endpoint(self, mock_db):
        """Verify PATCH /api/notifications/<id>/unread toggles is_read from 1 back to 0"""
        mock_db.return_value = self._get_mock_conn()

        self.notifications.append({
            "id": 10, "user_id": self.farmer1_id, "category": "crop", "title": "Wheat Planting",
            "message": "Remember to water", "severity": "info", "is_read": 1, "created_at": datetime.now()
        })

        res = self.client.patch(
            "/api/notifications/10/unread",
            headers={"Authorization": f"Bearer {self.farmer1_token}"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["unread_count"], 1)
        self.assertEqual(self.notifications[0]["is_read"], 0)

    @patch("routes.notification_routes.get_db_connection")
    def test_push_subscription_lifecycle(self, mock_db):
        """Verify POST, GET, and DELETE push subscriptions"""
        mock_db.return_value = self._get_mock_conn()

        # 1. Register subscription
        sub_payload = {
            "endpoint": "https://push.example.com/client-101",
            "p256dh": "mock-p256dh-key-xyz",
            "auth": "mock-auth-key-abc",
            "user_agent": "Mozilla/5.0 Mac Chrome/120"
        }
        res_sub = self.client.post(
            "/api/notifications/push-subscription",
            headers={"Authorization": f"Bearer {self.farmer1_token}", "Content-Type": "application/json"},
            data=json.dumps(sub_payload)
        )
        self.assertEqual(res_sub.status_code, 200)

        # 2. Check push status
        res_status = self.client.get(
            "/api/notifications/push-status",
            headers={"Authorization": f"Bearer {self.farmer1_token}"}
        )
        data_status = res_status.get_json()
        self.assertTrue(data_status.get("push_supported", False))
        self.assertEqual(data_status.get("active_subscriptions_count", 0), 1)

        # 3. Trigger test push
        res_test = self.client.post(
            "/api/notifications/test-push",
            headers={"Authorization": f"Bearer {self.farmer1_token}"}
        )
        self.assertEqual(res_test.status_code, 200)
        data_test = res_test.get_json()
        self.assertIn("push_payload", data_test)
        self.assertIn("AgriSmart", data_test["push_payload"]["title"])

        # 4. Unregister subscription
        res_del = self.client.delete(
            "/api/notifications/push-subscription",
            headers={"Authorization": f"Bearer {self.farmer1_token}", "Content-Type": "application/json"},
            data=json.dumps({"endpoint": "https://push.example.com/client-101"})
        )
        self.assertEqual(res_del.status_code, 200)
        self.assertEqual(len(self.push_subs), 0)

    @patch("routes.notification_routes.get_db_connection")
    def test_push_preference_toggle(self, mock_db):
        """Verify push_enabled preference can be stored and retrieved"""
        mock_db.return_value = self._get_mock_conn()

        # Save preferences with push_enabled = True
        res = self.client.put(
            "/api/notifications/preferences",
            headers={"Authorization": f"Bearer {self.farmer1_token}", "Content-Type": "application/json"},
            data=json.dumps({
                "crop_reminders": True,
                "irrigation_alerts": True,
                "weather_alerts": True,
                "disease_reminders": True,
                "push_enabled": True
            })
        )
        self.assertEqual(res.status_code, 200)

        # Fetch preferences
        res_get = self.client.get(
            "/api/notifications/preferences",
            headers={"Authorization": f"Bearer {self.farmer1_token}"}
        )
        prefs = res_get.get_json()["preferences"]
        self.assertTrue(prefs["push_enabled"])

    @patch("routes.notification_routes.get_db_connection")
    def test_farmer_data_isolation(self, mock_db):
        """Verify Farmer 1 cannot access, mark read, or delete Farmer 2's notifications"""
        mock_db.return_value = self._get_mock_conn()

        self.notifications.append({
            "id": 99, "user_id": self.farmer2_id, "category": "weather", "title": "Secret Alert",
            "message": "Only for farmer 2", "severity": "info", "is_read": 0, "created_at": datetime.now()
        })

        # Farmer 1 queries notifications list -> must be empty
        res = self.client.get(
            "/api/notifications",
            headers={"Authorization": f"Bearer {self.farmer1_token}"}
        )
        data = res.get_json()
        self.assertEqual(len(data["notifications"]), 0)

        # Farmer 1 attempts to mark read Farmer 2's notification -> 404
        res_read = self.client.patch(
            "/api/notifications/99/read",
            headers={"Authorization": f"Bearer {self.farmer1_token}"}
        )
        self.assertEqual(res_read.status_code, 404)

        # Farmer 1 attempts to delete Farmer 2's notification -> 404
        res_del = self.client.delete(
            "/api/notifications/99",
            headers={"Authorization": f"Bearer {self.farmer1_token}"}
        )
        self.assertEqual(res_del.status_code, 404)

        # Ensure notification still exists for Farmer 2
        self.assertEqual(len(self.notifications), 1)
        self.assertEqual(self.notifications[0]["is_read"], 0)


if __name__ == "__main__":
    unittest.main()
