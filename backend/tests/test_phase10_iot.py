import hashlib
import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app import app as flask_app
from utils.auth_tokens import create_access_token


class MockIoTCursor:
    def __init__(self, farms, crops, sensors, readings, thresholds, notifications):
        self.farms = farms
        self.crops = crops
        self.sensors = sensors
        self.readings = readings
        self.thresholds = thresholds
        self.notifications = notifications
        self.lastrowid = None
        self._res = None
        self.rowcount = 0

    def execute(self, query, params=None):
        q = " ".join(query.split()).upper()
        p = list(params) if params else []

        # SENSOR SELECTS
        if "FROM SENSORS S" in q and "WHERE S.USER_ID = %S" in q:
            uid = p[0]
            matched = []
            for s in sorted(self.sensors.values(), key=lambda x: x["id"], reverse=True):
                if s["user_id"] == uid:
                    f = self.farms.get(s["farm_id"], {})
                    c = self.crops.get(s.get("crop_id"), {})
                    t = self.thresholds.get(s["id"], {})
                    matched.append({
                        "id": s["id"],
                        "user_id": s["user_id"],
                        "farm_id": s["farm_id"],
                        "crop_id": s.get("crop_id"),
                        "device_id": s["device_id"],
                        "sensor_name": s["sensor_name"],
                        "sensor_type": s["sensor_type"],
                        "status": s.get("status", "disconnected"),
                        "last_reading_at": s.get("last_reading_at"),
                        "created_at": s.get("created_at", datetime.now()),
                        "updated_at": s.get("updated_at", datetime.now()),
                        "farm_name": f.get("farm_name", "Farm"),
                        "farm_location": f.get("location", ""),
                        "crop_name": c.get("crop_name"),
                        "crop_variety": c.get("variety"),
                        "min_value": t.get("min_value"),
                        "max_value": t.get("max_value"),
                        "threshold_enabled": t.get("is_enabled", 1)
                    })
            self._res = matched

        elif "FROM SENSORS S" in q and "WHERE S.DEVICE_ID = %S" in q:
            dev_id = p[0]
            for s in self.sensors.values():
                if s["device_id"] == dev_id:
                    self._res = [dict(s)]
                    return
            self._res = []

        elif "SELECT ID FROM SENSORS WHERE DEVICE_ID = %S" in q:
            dev_id = p[0]
            for s in self.sensors.values():
                if s["device_id"] == dev_id:
                    self._res = [{"id": s["id"]}]
                    return
            self._res = []

        elif "FROM SENSORS S" in q and "WHERE S.ID = %S AND S.USER_ID = %S" in q:
            sid, uid = p[0], p[1]
            s = self.sensors.get(sid)
            if s and s["user_id"] == uid:
                f = self.farms.get(s["farm_id"], {})
                c = self.crops.get(s.get("crop_id"), {})
                self._res = [{
                    "id": s["id"],
                    "sensor_name": s["sensor_name"],
                    "sensor_type": s["sensor_type"],
                    "device_id": s["device_id"],
                    "farm_name": f.get("farm_name", "Farm"),
                    "crop_name": c.get("crop_name")
                }]
            else:
                self._res = []

        elif "SELECT ID, SENSOR_NAME FROM SENSORS WHERE ID = %S AND USER_ID = %S" in q:
            sid, uid = p[0], p[1]
            s = self.sensors.get(sid)
            if s and s["user_id"] == uid:
                self._res = [{"id": s["id"], "sensor_name": s["sensor_name"]}]
            else:
                self._res = []

        elif "SELECT ID, DEVICE_ID FROM SENSORS WHERE ID = %S AND USER_ID = %S" in q:
            sid, uid = p[0], p[1]
            s = self.sensors.get(sid)
            if s and s["user_id"] == uid:
                self._res = [{"id": s["id"], "device_id": s["device_id"]}]
            else:
                self._res = []

        elif "SELECT ID, USER_ID, SENSOR_NAME, SENSOR_TYPE FROM SENSORS WHERE ID = %S AND USER_ID = %S" in q:
            sid, uid = p[0], p[1]
            s = self.sensors.get(sid)
            if s and s["user_id"] == uid:
                self._res = [{"id": s["id"], "user_id": s["user_id"], "sensor_name": s["sensor_name"], "sensor_type": s["sensor_type"]}]
            else:
                self._res = []

        elif "SELECT ID FROM SENSORS WHERE ID = %S AND USER_ID = %S" in q:
            sid, uid = p[0], p[1]
            s = self.sensors.get(sid)
            if s and s["user_id"] == uid:
                self._res = [{"id": s["id"]}]
            else:
                self._res = []

        elif "SELECT ID, LAST_READING_AT FROM SENSORS WHERE USER_ID = %S" in q:
            uid = p[0]
            self._res = [{"id": s["id"], "last_reading_at": s.get("last_reading_at")} for s in self.sensors.values() if s["user_id"] == uid]

        # FARMS & CROPS CHECKS
        elif "SELECT ID FROM FARMS WHERE ID = %S AND USER_ID = %S" in q:
            fid, uid = p[0], p[1]
            f = self.farms.get(fid)
            if f and f["user_id"] == uid:
                self._res = [{"id": f["id"]}]
            else:
                self._res = []

        elif "SELECT ID FROM CROPS WHERE ID = %S AND USER_ID = %S" in q:
            cid, uid = p[0], p[1]
            c = self.crops.get(cid)
            if c and c["user_id"] == uid:
                self._res = [{"id": c["id"]}]
            else:
                self._res = []

        # SENSOR INSERTS / UPDATES / DELETES
        elif "INSERT INTO SENSORS" in q:
            new_id = max(self.sensors.keys(), default=0) + 1
            self.sensors[new_id] = {
                "id": new_id,
                "user_id": p[0],
                "farm_id": p[1],
                "crop_id": p[2],
                "device_id": p[3],
                "device_key_hash": p[4],
                "sensor_name": p[5],
                "sensor_type": p[6],
                "status": "disconnected",
                "last_reading_at": None,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            self.lastrowid = new_id
            self._res = []

        elif "UPDATE SENSORS SET STATUS = 'CONNECTED', LAST_READING_AT = %S" in q:
            last_ts, sid = p[0], p[1]
            if sid in self.sensors:
                self.sensors[sid]["status"] = "connected"
                self.sensors[sid]["last_reading_at"] = last_ts
            self._res = []

        elif "UPDATE SENSORS SET SENSOR_NAME = %S WHERE ID = %S" in q:
            name, sid = p[0], p[1]
            if sid in self.sensors:
                self.sensors[sid]["sensor_name"] = name
            self._res = []

        elif "UPDATE SENSORS SET DEVICE_KEY_HASH = %S" in q:
            key_hash, sid = p[0], p[1]
            if sid in self.sensors:
                self.sensors[sid]["device_key_hash"] = key_hash
            self._res = []

        elif "DELETE FROM SENSORS WHERE ID = %S" in q:
            sid = p[0]
            self.sensors.pop(sid, None)
            self._res = []

        # THRESHOLDS
        elif "INSERT INTO SENSOR_THRESHOLDS" in q:
            sid, uid, min_v, max_v = p[0], p[1], p[2], p[3]
            self.thresholds[sid] = {"sensor_id": sid, "user_id": uid, "min_value": min_v, "max_value": max_v, "is_enabled": 1}
            self._res = []

        elif "SELECT MIN_VALUE, MAX_VALUE, IS_ENABLED FROM SENSOR_THRESHOLDS WHERE SENSOR_ID = %S" in q:
            sid = p[0]
            t = self.thresholds.get(sid)
            self._res = [dict(t)] if t else []

        # READINGS
        elif "INSERT INTO SENSOR_READINGS" in q:
            new_id = max(self.readings.keys(), default=0) + 1
            is_demo = 1 if ",1," in q.replace(" ", "") else 0
            self.readings[new_id] = {
                "id": new_id,
                "sensor_id": p[0],
                "user_id": p[1],
                "sensor_type": p[2],
                "value": p[3],
                "unit": p[4],
                "is_demo": is_demo,
                "recorded_at": p[5],
                "created_at": datetime.now()
            }
            self.lastrowid = new_id
            self._res = []

        elif "FROM SENSOR_READINGS" in q and "ORDER BY RECORDED_AT DESC LIMIT 1" in q and "SENSOR_ID = %S" in q:
            sid = p[0]
            sensor_r = [r for r in self.readings.values() if r["sensor_id"] == sid]
            if sensor_r:
                sensor_r.sort(key=lambda x: x["recorded_at"], reverse=True)
                self._res = [sensor_r[0]]
            else:
                self._res = []

        elif "DELETE FROM SENSOR_READINGS" in q:
            sid = p[0]
            to_del = [rid for rid, r in self.readings.items() if r["sensor_id"] == sid and r["is_demo"] == 1]
            for rid in to_del:
                del self.readings[rid]
            self.rowcount = len(to_del)
            self._res = []

        elif "FROM SENSOR_READINGS WHERE SENSOR_ID = %S" in q:
            sid = p[0]
            res = [r for r in self.readings.values() if r["sensor_id"] == sid]
            res.sort(key=lambda x: x["recorded_at"])
            self._res = res

        # NOTIFICATIONS
        elif "SELECT ID FROM NOTIFICATIONS WHERE USER_ID = %S AND UNIQUE_KEY = %S" in q:
            uid, ukey = p[0], p[1]
            found = [n for n in self.notifications.values() if n["user_id"] == uid and n.get("unique_key") == ukey]
            self._res = found

        elif "INSERT INTO NOTIFICATIONS" in q:
            nid = max(self.notifications.keys(), default=0) + 1
            self.notifications[nid] = {
                "id": nid,
                "user_id": p[0],
                "category": p[1],
                "title": p[2],
                "message": p[3],
                "severity": p[4],
                "link": p[5],
                "unique_key": p[6],
                "is_read": 0
            }
            self._res = []

        # IRRIGATION SYNC
        elif "ORDER BY R.IS_DEMO ASC" in q:
            uid = p[0]
            moist_r = [
                r for r in self.readings.values()
                if r["user_id"] == uid and r["sensor_type"] == "soil_moisture"
            ]
            if moist_r:
                # Real readings first, then latest
                moist_r.sort(key=lambda x: (x["is_demo"], -x["recorded_at"].timestamp()))
                r = moist_r[0]
                s = self.sensors.get(r["sensor_id"], {})
                f = self.farms.get(s.get("farm_id"), {})
                c = self.crops.get(s.get("crop_id"), {})
                self._res = [{
                    "id": r["id"],
                    "value": r["value"],
                    "unit": r["unit"],
                    "is_demo": r["is_demo"],
                    "recorded_at": r["recorded_at"],
                    "sensor_name": s.get("sensor_name", "Sensor"),
                    "farm_name": f.get("farm_name", "Farm"),
                    "crop_name": c.get("crop_name")
                }]
            else:
                self._res = []

        # OVERVIEW LATEST READINGS BY CATEGORY
        elif "FROM SENSOR_READINGS R JOIN SENSORS S" in q and "LIMIT 1" in q:
            uid = p[0]
            cat = p[1]
            cat_readings = [
                r for r in self.readings.values()
                if r["user_id"] == uid and r["sensor_type"] == cat
            ]
            if cat_readings:
                cat_readings.sort(key=lambda x: x["recorded_at"], reverse=True)
                r = cat_readings[0]
                s = self.sensors.get(r["sensor_id"], {})
                f = self.farms.get(s.get("farm_id"), {})
                c = self.crops.get(s.get("crop_id"), {})
                self._res = [{
                    "value": r["value"],
                    "unit": r["unit"],
                    "is_demo": r["is_demo"],
                    "recorded_at": r["recorded_at"],
                    "sensor_name": s.get("sensor_name", "Sensor"),
                    "sensor_type": s.get("sensor_type", cat),
                    "farm_name": f.get("farm_name", "Farm"),
                    "crop_name": c.get("crop_name")
                }]
            else:
                self._res = []

        else:
            self._res = []

    def fetchall(self):
        res = self._res if self._res is not None else []
        self._res = None
        return res

    def fetchone(self):
        res = self._res if self._res is not None else []
        self._res = None
        return res[0] if res else None

    def close(self):
        pass


class MockIoTConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, dictionary=False):
        return self._cursor

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


class TestPhase10IoTMonitoring(unittest.TestCase):
    def setUp(self):
        self.client = flask_app.test_client()
        self.farmer1_id = 1
        self.farmer2_id = 2
        self.token1 = create_access_token(self.farmer1_id)
        self.token2 = create_access_token(self.farmer2_id)

        self.farms = {
            1: {"id": 1, "user_id": 1, "farm_name": "Sahyadri Agro", "location": "Nashik", "total_area": 10.0, "area_unit": "acre"},
            2: {"id": 2, "user_id": 2, "farm_name": "Godavari Farm", "location": "Pune", "total_area": 15.0, "area_unit": "acre"}
        }

        self.crops = {
            1: {"id": 1, "user_id": 1, "farm_id": 1, "crop_name": "Wheat", "variety": "HD-2967"},
            2: {"id": 2, "user_id": 2, "farm_id": 2, "crop_name": "Cotton", "variety": "Bt-2"}
        }

        self.sensors = {}
        self.readings = {}
        self.thresholds = {}
        self.notifications = {}

    def _get_mock_conn(self):
        cursor = MockIoTCursor(self.farms, self.crops, self.sensors, self.readings, self.thresholds, self.notifications)
        return MockIoTConnection(cursor)

    # -------------------------------------------------------------
    # 1. SENSOR REGISTRATION & REMOVAL
    # -------------------------------------------------------------
    @patch("routes.iot_routes.get_db_connection")
    def test_sensor_registration_and_removal(self, mock_db):
        mock_db.return_value = self._get_mock_conn()

        # Register Soil Moisture Sensor
        resp = self.client.post(
            "/api/iot/sensors",
            headers={"Authorization": f"Bearer {self.token1}"},
            json={
                "farm_id": 1,
                "crop_id": 1,
                "device_id": "ESP32-SOIL-01",
                "sensor_name": "North Field Probe",
                "sensor_type": "soil_moisture",
                "min_value": 25.0,
                "max_value": 75.0
            }
        )
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)
        self.assertEqual(data["status"], "success")
        self.assertIn("device_key", data["sensor"])
        device_key = data["sensor"]["device_key"]
        self.assertTrue(device_key.startswith("agy_dev_"))

        # Verify listed
        resp2 = self.client.get(
            "/api/iot/sensors",
            headers={"Authorization": f"Bearer {self.token1}"}
        )
        self.assertEqual(resp2.status_code, 200)
        sensors = json.loads(resp2.data)["sensors"]
        self.assertEqual(len(sensors), 1)
        self.assertEqual(sensors[0]["device_id"], "ESP32-SOIL-01")
        # Ensure raw device key or hash is never exposed in listing
        self.assertNotIn("device_key", sensors[0])
        self.assertNotIn("device_key_hash", sensors[0])

        # Delete sensor
        sid = sensors[0]["id"]
        del_resp = self.client.delete(
            f"/api/iot/sensors/{sid}",
            headers={"Authorization": f"Bearer {self.token1}"}
        )
        self.assertEqual(del_resp.status_code, 200)
        self.assertEqual(len(self.sensors), 0)

    # -------------------------------------------------------------
    # 2. HARDWARE INGESTION & DEVICE AUTHENTICATION
    # -------------------------------------------------------------
    @patch("routes.iot_routes.get_db_connection")
    def test_hardware_device_ingestion(self, mock_db):
        mock_db.return_value = self._get_mock_conn()

        # Pre-seed registered sensor
        raw_key = "agy_dev_testsecretkey123456789"
        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        self.sensors[1] = {
            "id": 1,
            "user_id": 1,
            "farm_id": 1,
            "crop_id": 1,
            "device_id": "ESP32-MOIST-99",
            "device_key_hash": key_hash,
            "sensor_name": "West Field Sensor",
            "sensor_type": "soil_moisture",
            "status": "disconnected",
            "last_reading_at": None
        }

        # Successful Ingestion
        resp = self.client.post(
            "/api/iot/ingest",
            headers={
                "X-Device-Id": "ESP32-MOIST-99",
                "X-Device-Key": raw_key
            },
            json={
                "sensor_type": "soil_moisture",
                "value": 34.2,
                "unit": "%",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["status"], "success")

        # Verify reading saved and sensor marked connected
        self.assertEqual(len(self.readings), 1)
        r = list(self.readings.values())[0]
        self.assertEqual(r["value"], 34.2)
        self.assertEqual(r["is_demo"], 0)
        self.assertEqual(self.sensors[1]["status"], "connected")

        # Invalid device key -> 401
        resp_bad_key = self.client.post(
            "/api/iot/ingest",
            headers={
                "X-Device-Id": "ESP32-MOIST-99",
                "X-Device-Key": "wrong_key"
            },
            json={"value": 35.0}
        )
        self.assertEqual(resp_bad_key.status_code, 401)

        # Unregistered device ID -> 401
        resp_unreg = self.client.post(
            "/api/iot/ingest",
            headers={
                "X-Device-Id": "UNKNOWN-DEVICE",
                "X-Device-Key": raw_key
            },
            json={"value": 35.0}
        )
        self.assertEqual(resp_unreg.status_code, 401)

    # -------------------------------------------------------------
    # 3. READING VALUE VALIDATION
    # -------------------------------------------------------------
    @patch("routes.iot_routes.get_db_connection")
    def test_reading_validation(self, mock_db):
        mock_db.return_value = self._get_mock_conn()

        raw_key = "agy_dev_valkey12345"
        self.sensors[1] = {
            "id": 1,
            "user_id": 1,
            "farm_id": 1,
            "device_id": "ESP32-TEST-VAL",
            "device_key_hash": hashlib.sha256(raw_key.encode()).hexdigest(),
            "sensor_name": "Test Val",
            "sensor_type": "soil_moisture"
        }

        # Soil moisture > 100% is physically invalid
        resp_out_of_bounds = self.client.post(
            "/api/iot/ingest",
            headers={"X-Device-Id": "ESP32-TEST-VAL", "X-Device-Key": raw_key},
            json={"value": 150.0}
        )
        self.assertEqual(resp_out_of_bounds.status_code, 400)

        # Future timestamp (> 5 minutes ahead)
        future_ts = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        resp_future = self.client.post(
            "/api/iot/ingest",
            headers={"X-Device-Id": "ESP32-TEST-VAL", "X-Device-Key": raw_key},
            json={"value": 45.0, "timestamp": future_ts}
        )
        self.assertEqual(resp_future.status_code, 400)

    # -------------------------------------------------------------
    # 4. MULTI-READING INGESTION (DHT22 COMBINED)
    # -------------------------------------------------------------
    @patch("routes.iot_routes.get_db_connection")
    def test_multi_reading_ingestion(self, mock_db):
        mock_db.return_value = self._get_mock_conn()

        raw_key = "agy_dev_dht22_key"
        self.sensors[1] = {
            "id": 1,
            "user_id": 1,
            "farm_id": 1,
            "device_id": "ESP32-DHT22-01",
            "device_key_hash": hashlib.sha256(raw_key.encode()).hexdigest(),
            "sensor_name": "Greenhouse Temp/Humidity",
            "sensor_type": "air_temp_humidity"
        }

        resp = self.client.post(
            "/api/iot/ingest",
            headers={"X-Device-Id": "ESP32-DHT22-01", "X-Device-Key": raw_key},
            json={
                "readings": [
                    {"sensor_type": "air_temp", "value": 28.5, "unit": "°C"},
                    {"sensor_type": "air_humidity", "value": 64.0, "unit": "%"}
                ]
            }
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(self.readings), 2)

    # -------------------------------------------------------------
    # 5. FARMER TENANT DATA ISOLATION
    # -------------------------------------------------------------
    @patch("routes.iot_routes.get_db_connection")
    def test_farmer_data_isolation(self, mock_db):
        mock_db.return_value = self._get_mock_conn()

        # Farmer 1 sensor
        self.sensors[1] = {
            "id": 1,
            "user_id": 1,
            "farm_id": 1,
            "device_id": "ESP32-F1",
            "device_key_hash": "hash1",
            "sensor_name": "Farmer 1 Sensor",
            "sensor_type": "soil_moisture"
        }

        # Farmer 2 tries to delete Farmer 1's sensor -> 404
        del_resp = self.client.delete(
            "/api/iot/sensors/1",
            headers={"Authorization": f"Bearer {self.token2}"}
        )
        self.assertEqual(del_resp.status_code, 404)

        # Farmer 2 tries to inject demo into Farmer 1's sensor -> 404
        demo_resp = self.client.post(
            "/api/iot/sensors/1/demo",
            headers={"Authorization": f"Bearer {self.token2}"},
            json={"value": 30.0}
        )
        self.assertEqual(demo_resp.status_code, 404)

        # Farmer 2 cannot register sensor on Farmer 1's farm (farm_id=1)
        reg_resp = self.client.post(
            "/api/iot/sensors",
            headers={"Authorization": f"Bearer {self.token2}"},
            json={
                "farm_id": 1,
                "device_id": "ESP32-STEAL",
                "sensor_name": "Illegal",
                "sensor_type": "soil_moisture"
            }
        )
        self.assertEqual(reg_resp.status_code, 400)

    # -------------------------------------------------------------
    # 6. MANUAL DEMO MODE
    # -------------------------------------------------------------
    @patch("routes.iot_routes.get_db_connection")
    def test_manual_demo_mode(self, mock_db):
        mock_db.return_value = self._get_mock_conn()

        self.sensors[1] = {
            "id": 1,
            "user_id": 1,
            "farm_id": 1,
            "device_id": "ESP32-DEMO-TEST",
            "device_key_hash": "hash",
            "sensor_name": "Demo Sensor",
            "sensor_type": "soil_moisture",
            "status": "disconnected",
            "last_reading_at": None
        }

        # Inject demo reading
        resp = self.client.post(
            "/api/iot/sensors/1/demo",
            headers={"Authorization": f"Bearer {self.token1}"},
            json={"value": 42.5, "unit": "%"}
        )
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)
        self.assertTrue(data["is_demo"])
        self.assertEqual(len(self.readings), 1)
        self.assertEqual(list(self.readings.values())[0]["is_demo"], 1)

        # Clear demo readings
        del_resp = self.client.delete(
            "/api/iot/sensors/1/demo",
            headers={"Authorization": f"Bearer {self.token1}"}
        )
        self.assertEqual(del_resp.status_code, 200)
        self.assertEqual(len(self.readings), 0)

    # -------------------------------------------------------------
    # 7. SENSOR HISTORY & STATISTICS (MIN, MAX, AVG)
    # -------------------------------------------------------------
    @patch("routes.iot_routes.get_db_connection")
    def test_sensor_history_and_stats(self, mock_db):
        mock_db.return_value = self._get_mock_conn()

        self.sensors[1] = {
            "id": 1,
            "user_id": 1,
            "farm_id": 1,
            "crop_id": 1,
            "device_id": "ESP32-HIST-01",
            "device_key_hash": "hash",
            "sensor_name": "History Sensor",
            "sensor_type": "soil_moisture"
        }

        now = datetime.now()
        self.readings[1] = {"id": 1, "sensor_id": 1, "user_id": 1, "sensor_type": "soil_moisture", "value": 20.0, "unit": "%", "is_demo": 0, "recorded_at": now - timedelta(hours=2)}
        self.readings[2] = {"id": 2, "sensor_id": 1, "user_id": 1, "sensor_type": "soil_moisture", "value": 40.0, "unit": "%", "is_demo": 0, "recorded_at": now - timedelta(hours=1)}
        self.readings[3] = {"id": 3, "sensor_id": 1, "user_id": 1, "sensor_type": "soil_moisture", "value": 60.0, "unit": "%", "is_demo": 0, "recorded_at": now}

        resp = self.client.get(
            "/api/iot/sensors/1/history?range=24h",
            headers={"Authorization": f"Bearer {self.token1}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        stats = data["stats"]
        self.assertEqual(stats["count"], 3)
        self.assertEqual(stats["min"], 20.0)
        self.assertEqual(stats["max"], 60.0)
        self.assertEqual(stats["avg"], 40.0)

    # -------------------------------------------------------------
    # 8. THRESHOLD ALERTS & DUPLICATE PREVENTION
    # -------------------------------------------------------------
    @patch("routes.iot_routes.get_db_connection")
    def test_threshold_alerts_and_duplicate_prevention(self, mock_db):
        mock_db.return_value = self._get_mock_conn()

        raw_key = "agy_dev_alert_key"
        self.sensors[1] = {
            "id": 1,
            "user_id": 1,
            "farm_id": 1,
            "device_id": "ESP32-ALERT-01",
            "device_key_hash": hashlib.sha256(raw_key.encode()).hexdigest(),
            "sensor_name": "Alert Probe",
            "sensor_type": "soil_moisture"
        }
        self.thresholds[1] = {
            "sensor_id": 1,
            "user_id": 1,
            "min_value": 20.0,
            "max_value": 80.0,
            "is_enabled": 1
        }

        # Send reading below threshold (12% < 20%)
        resp1 = self.client.post(
            "/api/iot/ingest",
            headers={"X-Device-Id": "ESP32-ALERT-01", "X-Device-Key": raw_key},
            json={"value": 12.0}
        )
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(len(self.notifications), 1)
        alert = list(self.notifications.values())[0]
        self.assertIn("Low", alert["title"])

        # Send another low reading immediately -> Duplicate notification prevented
        resp2 = self.client.post(
            "/api/iot/ingest",
            headers={"X-Device-Id": "ESP32-ALERT-01", "X-Device-Key": raw_key},
            json={"value": 11.5}
        )
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(len(self.notifications), 1)  # Still 1, no duplicate

    # -------------------------------------------------------------
    # 9. SMART IRRIGATION INTEGRATION SYNC
    # -------------------------------------------------------------
    @patch("routes.iot_routes.get_db_connection")
    def test_irrigation_sync_integration(self, mock_db):
        mock_db.return_value = self._get_mock_conn()

        self.sensors[1] = {
            "id": 1,
            "user_id": 1,
            "farm_id": 1,
            "crop_id": 1,
            "device_id": "ESP32-IRRIG-01",
            "device_key_hash": "hash",
            "sensor_name": "Wheat Field Sensor",
            "sensor_type": "soil_moisture"
        }
        self.readings[1] = {
            "id": 1,
            "sensor_id": 1,
            "user_id": 1,
            "sensor_type": "soil_moisture",
            "value": 31.8,
            "unit": "%",
            "is_demo": 0,
            "recorded_at": datetime.now()
        }

        # Query sync for Wheat
        resp = self.client.get(
            "/api/iot/irrigation-sync?crop=Wheat",
            headers={"Authorization": f"Bearer {self.token1}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["has_sensor_data"])
        self.assertEqual(data["soil_moisture"], 31.8)
        self.assertFalse(data["is_demo"])

    # -------------------------------------------------------------
    # 10. REGENERATE DEVICE KEY
    # -------------------------------------------------------------
    @patch("routes.iot_routes.get_db_connection")
    def test_regenerate_device_key(self, mock_db):
        mock_db.return_value = self._get_mock_conn()

        old_key = "agy_dev_old_key"
        self.sensors[1] = {
            "id": 1,
            "user_id": 1,
            "farm_id": 1,
            "device_id": "ESP32-ROT-01",
            "device_key_hash": hashlib.sha256(old_key.encode()).hexdigest(),
            "sensor_name": "Key Rotation Sensor",
            "sensor_type": "soil_moisture"
        }

        resp = self.client.post(
            "/api/iot/sensors/1/regenerate-key",
            headers={"Authorization": f"Bearer {self.token1}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        new_key = data["device_key"]
        self.assertNotEqual(new_key, old_key)

        # Ingest with old key -> 401
        resp_old = self.client.post(
            "/api/iot/ingest",
            headers={"X-Device-Id": "ESP32-ROT-01", "X-Device-Key": old_key},
            json={"value": 35.0}
        )
        self.assertEqual(resp_old.status_code, 401)

        # Ingest with new key -> 200
        resp_new = self.client.post(
            "/api/iot/ingest",
            headers={"X-Device-Id": "ESP32-ROT-01", "X-Device-Key": new_key},
            json={"value": 35.0}
        )
        self.assertEqual(resp_new.status_code, 200)


if __name__ == "__main__":
    unittest.main()
