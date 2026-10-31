import json
import os
import sys
import unittest
from datetime import date, datetime
from unittest.mock import patch

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app import app as flask_app
from utils.auth_tokens import create_access_token


class MockFarmCropCursor:
    def __init__(self, farms_db, crops_db):
        self.farms_db = farms_db
        self.crops_db = crops_db
        self.lastrowid = None
        self._current_result = None

    def execute(self, query, params=None):
        clean_q = " ".join(query.split()).upper()
        params = list(params) if params else []

        # -------------------------------------------------------------
        # FARMS QUERIES
        # -------------------------------------------------------------
        if "FROM FARMS F LEFT JOIN CROPS C ON C.FARM_ID = F.ID WHERE F.USER_ID = %S GROUP BY F.ID" in clean_q:
            user_id = params[0]
            results = []
            for f in self.farms_db.values():
                if f["user_id"] == user_id:
                    crop_count = sum(1 for c in self.crops_db.values() if c.get("farm_id") == f["id"])
                    results.append({
                        "id": f["id"],
                        "farm_name": f["farm_name"],
                        "location": f["location"],
                        "total_area": str(f["total_area"]),
                        "area_unit": f["area_unit"],
                        "crop_count": crop_count,
                        "created_at": f.get("created_at"),
                        "updated_at": f.get("updated_at")
                    })
            results.sort(key=lambda x: x["id"], reverse=True)
            self._current_result = results

        elif "SELECT F.ID, F.FARM_NAME, F.LOCATION, CAST(F.TOTAL_AREA AS CHAR) AS TOTAL_AREA, F.AREA_UNIT, F.CREATED_AT, F.UPDATED_AT, COUNT(C.ID) AS CROP_COUNT FROM FARMS F LEFT JOIN CROPS C ON C.FARM_ID = F.ID WHERE F.ID = %S AND F.USER_ID = %S" in clean_q:
            farm_id = params[0]
            user_id = params[1]
            farm = self.farms_db.get(farm_id)
            if farm and farm["user_id"] == user_id:
                crop_count = sum(1 for c in self.crops_db.values() if c.get("farm_id") == farm["id"])
                self._current_result = [{
                    "id": farm["id"],
                    "farm_name": farm["farm_name"],
                    "location": farm["location"],
                    "total_area": str(farm["total_area"]),
                    "area_unit": farm["area_unit"],
                    "crop_count": crop_count,
                    "created_at": farm.get("created_at"),
                    "updated_at": farm.get("updated_at")
                }]
            else:
                self._current_result = []

        elif "SELECT ID FROM FARMS WHERE ID = %S AND USER_ID = %S" in clean_q:
            farm_id = params[0]
            user_id = params[1]
            farm = self.farms_db.get(farm_id)
            if farm and farm["user_id"] == user_id:
                self._current_result = [{"id": farm["id"]}]
            else:
                self._current_result = []

        elif "SELECT ID, FARM_NAME FROM FARMS WHERE ID = %S AND USER_ID = %S" in clean_q:
            farm_id = params[0]
            user_id = params[1]
            farm = self.farms_db.get(farm_id)
            if farm and farm["user_id"] == user_id:
                self._current_result = [{"id": farm["id"], "farm_name": farm["farm_name"]}]
            else:
                self._current_result = []

        elif "INSERT INTO FARMS" in clean_q:
            # (user_id, farm_name, location, total_area, area_unit)
            new_id = (max(self.farms_db.keys()) if self.farms_db else 0) + 1
            self.lastrowid = new_id
            self.farms_db[new_id] = {
                "id": new_id,
                "user_id": params[0],
                "farm_name": params[1],
                "location": params[2],
                "total_area": params[3],
                "area_unit": params[4],
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            self._current_result = None

        elif "UPDATE FARMS" in clean_q:
            # SET farm_name = %s, location = %s, total_area = %s, area_unit = %s WHERE id = %s AND user_id = %s
            farm_name, location, total_area, area_unit, farm_id, user_id = params
            farm = self.farms_db.get(farm_id)
            if farm and farm["user_id"] == user_id:
                farm["farm_name"] = farm_name
                farm["location"] = location
                farm["total_area"] = total_area
                farm["area_unit"] = area_unit
                farm["updated_at"] = datetime.now()
            self._current_result = None

        elif "DELETE FROM FARMS WHERE ID = %S AND USER_ID = %S" in clean_q:
            farm_id, user_id = params
            farm = self.farms_db.get(farm_id)
            if farm and farm["user_id"] == user_id:
                del self.farms_db[farm_id]
                # Cascade delete crops
                to_del = [cid for cid, c in self.crops_db.items() if c.get("farm_id") == farm_id]
                for cid in to_del:
                    del self.crops_db[cid]
            self._current_result = None

        # -------------------------------------------------------------
        # CROPS QUERIES
        # -------------------------------------------------------------
        elif "FROM CROPS C LEFT JOIN FARMS F ON F.ID = C.FARM_ID WHERE C.USER_ID = %S" in clean_q:
            user_id = params[0]
            farm_id = params[1] if len(params) > 1 else None
            results = []
            for c in self.crops_db.values():
                if c["user_id"] == user_id:
                    if farm_id is not None and c.get("farm_id") != farm_id:
                        continue
                    farm = self.farms_db.get(c.get("farm_id"))
                    results.append({
                        "id": c["id"],
                        "user_id": c["user_id"],
                        "farm_id": c.get("farm_id"),
                        "farm_name": farm["farm_name"] if farm else None,
                        "crop_name": c["crop_name"],
                        "variety": c.get("variety"),
                        "planting_date": c.get("planting_date"),
                        "cultivated_area": str(c.get("cultivated_area")) if c.get("cultivated_area") else None,
                        "area_unit": c.get("area_unit"),
                        "growth_status": c.get("growth_status"),
                        "expected_harvest_date": c.get("expected_harvest_date"),
                        "notes": c.get("notes"),
                        "created_at": c.get("created_at"),
                        "updated_at": c.get("updated_at")
                    })
            results.sort(key=lambda x: x["id"], reverse=True)
            self._current_result = results

        elif "SELECT C.*, F.FARM_NAME, CAST(C.CULTIVATED_AREA AS CHAR) AS CULTIVATED_AREA_STR FROM CROPS C LEFT JOIN FARMS F ON F.ID = C.FARM_ID WHERE C.ID = %S AND C.USER_ID = %S" in clean_q:
            crop_id, user_id = params
            crop = self.crops_db.get(crop_id)
            if crop and crop["user_id"] == user_id:
                farm = self.farms_db.get(crop.get("farm_id"))
                self._current_result = [{
                    "id": crop["id"],
                    "user_id": crop["user_id"],
                    "farm_id": crop.get("farm_id"),
                    "farm_name": farm["farm_name"] if farm else None,
                    "crop_name": crop["crop_name"],
                    "variety": crop.get("variety"),
                    "planting_date": crop.get("planting_date"),
                    "cultivated_area_str": str(crop.get("cultivated_area")) if crop.get("cultivated_area") else None,
                    "area_unit": crop.get("area_unit"),
                    "growth_status": crop.get("growth_status"),
                    "expected_harvest_date": crop.get("expected_harvest_date"),
                    "notes": crop.get("notes"),
                    "created_at": crop.get("created_at"),
                    "updated_at": crop.get("updated_at")
                }]
            else:
                self._current_result = []

        elif "SELECT ID, CROP_NAME FROM CROPS WHERE ID = %S AND USER_ID = %S" in clean_q:
            crop_id, user_id = params
            crop = self.crops_db.get(crop_id)
            if crop and crop["user_id"] == user_id:
                self._current_result = [{"id": crop["id"], "crop_name": crop["crop_name"]}]
            else:
                self._current_result = []

        elif "SELECT ID FROM CROPS WHERE ID = %S AND USER_ID = %S" in clean_q:
            crop_id, user_id = params
            crop = self.crops_db.get(crop_id)
            if crop and crop["user_id"] == user_id:
                self._current_result = [{"id": crop["id"]}]
            else:
                self._current_result = []

        elif "INSERT INTO CROPS" in clean_q:
            # (user_id, farm_id, crop_name, variety, planting_date, cultivated_area, area_unit, expected_harvest_date, growth_status, notes)
            new_id = (max(self.crops_db.keys()) if self.crops_db else 0) + 1
            self.lastrowid = new_id
            self.crops_db[new_id] = {
                "id": new_id,
                "user_id": params[0],
                "farm_id": params[1],
                "crop_name": params[2],
                "variety": params[3],
                "planting_date": params[4],
                "cultivated_area": params[5],
                "area_unit": params[6],
                "expected_harvest_date": params[7],
                "growth_status": params[8],
                "notes": params[9],
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            self._current_result = None

        elif "UPDATE CROPS SET FARM_ID = %S, CROP_NAME = %S, VARIETY = %S" in clean_q:
            farm_id, crop_name, variety, p_date, c_area, a_unit, h_date, g_status, notes, crop_id, user_id = params
            crop = self.crops_db.get(crop_id)
            if crop and crop["user_id"] == user_id:
                crop["farm_id"] = farm_id
                crop["crop_name"] = crop_name
                crop["variety"] = variety
                crop["planting_date"] = p_date
                crop["cultivated_area"] = c_area
                crop["area_unit"] = a_unit
                crop["expected_harvest_date"] = h_date
                crop["growth_status"] = g_status
                crop["notes"] = notes
                crop["updated_at"] = datetime.now()
            self._current_result = None

        elif "UPDATE CROPS SET GROWTH_STATUS = %S WHERE ID = %S AND USER_ID = %S" in clean_q:
            status, crop_id, user_id = params
            crop = self.crops_db.get(crop_id)
            if crop and crop["user_id"] == user_id:
                crop["growth_status"] = status
                crop["updated_at"] = datetime.now()
            self._current_result = None

        elif "DELETE FROM CROPS WHERE ID = %S AND USER_ID = %S" in clean_q:
            crop_id, user_id = params
            crop = self.crops_db.get(crop_id)
            if crop and crop["user_id"] == user_id:
                del self.crops_db[crop_id]
            self._current_result = None

        # -------------------------------------------------------------
        # DASHBOARD SUMMARY QUERIES
        # -------------------------------------------------------------
        elif "SELECT COUNT(*) AS TOTAL FROM FARMS WHERE USER_ID = %S" in clean_q:
            user_id = params[0]
            count = sum(1 for f in self.farms_db.values() if f["user_id"] == user_id)
            self._current_result = [{"total": count}]

        elif "SELECT COUNT(*) AS TOTAL FROM CROPS WHERE USER_ID = %S AND GROWTH_STATUS IN ('GROWING', 'FLOWERING', 'FRUITING')" in clean_q:
            user_id = params[0]
            count = sum(1 for c in self.crops_db.values() if c["user_id"] == user_id and c.get("growth_status") in ("Growing", "Flowering", "Fruiting"))
            self._current_result = [{"total": count}]

        elif "SELECT COUNT(*) AS TOTAL FROM CROPS WHERE USER_ID = %S AND GROWTH_STATUS = 'READY FOR HARVEST'" in clean_q:
            user_id = params[0]
            count = sum(1 for c in self.crops_db.values() if c["user_id"] == user_id and c.get("growth_status") == "Ready for Harvest")
            self._current_result = [{"total": count}]

        elif "SELECT COUNT(*) AS TOTAL FROM CROPS WHERE USER_ID = %S" in clean_q:
            user_id = params[0]
            count = sum(1 for c in self.crops_db.values() if c["user_id"] == user_id)
            self._current_result = [{"total": count}]

        elif "SELECT GROWTH_STATUS, COUNT(*) AS COUNT FROM CROPS WHERE USER_ID = %S GROUP BY GROWTH_STATUS" in clean_q:
            user_id = params[0]
            counts = {}
            for c in self.crops_db.values():
                if c["user_id"] == user_id:
                    st = c.get("growth_status", "Newly Planted")
                    counts[st] = counts.get(st, 0) + 1
            self._current_result = [{"growth_status": k, "count": v} for k, v in counts.items()]

        else:
            self._current_result = []

    def fetchone(self):
        if self._current_result and len(self._current_result) > 0:
            return self._current_result[0]
        return None

    def fetchall(self):
        return self._current_result if self._current_result is not None else []

    def close(self):
        pass


class MockFarmCropConnection:
    def __init__(self, farms_db, crops_db):
        self.farms_db = farms_db
        self.crops_db = crops_db

    def cursor(self, dictionary=False):
        return MockFarmCropCursor(self.farms_db, self.crops_db)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


class TestPhase6FarmCropManagement(unittest.TestCase):
    def setUp(self):
        self.client = flask_app.test_client()
        self.farms_db = {}
        self.crops_db = {}

        self.db_patcher = patch(
            "routes.farm_crop_routes.get_db_connection",
            side_effect=lambda: MockFarmCropConnection(self.farms_db, self.crops_db)
        )
        self.db_patcher.start()

        self.user1_id = 101
        self.user2_id = 102

        self.token1 = create_access_token(self.user1_id)
        self.token2 = create_access_token(self.user2_id)

        self.headers1 = {
            "Authorization": f"Bearer {self.token1}",
            "Content-Type": "application/json"
        }
        self.headers2 = {
            "Authorization": f"Bearer {self.token2}",
            "Content-Type": "application/json"
        }

    def tearDown(self):
        self.db_patcher.stop()

    # =========================================================================
    # FARMS TESTS
    # =========================================================================

    def test_list_farms_empty(self):
        resp = self.client.get("/api/farms", headers=self.headers1)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["farms"], [])

    def test_add_farm_success(self):
        payload = {
            "farm_name": "Sunrise Orchard",
            "location": "Nashik, Maharashtra",
            "total_area": 15.5,
            "area_unit": "acre"
        }
        resp = self.client.post("/api/farms", headers=self.headers1, data=json.dumps(payload))
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["farm"]["farm_name"], "Sunrise Orchard")
        self.assertEqual(data["farm"]["total_area"], 15.5)
        self.assertEqual(data["farm"]["area_unit"], "acre")

        # Verify listed
        list_resp = self.client.get("/api/farms", headers=self.headers1)
        farms = list_resp.get_json()["farms"]
        self.assertEqual(len(farms), 1)
        self.assertEqual(farms[0]["farm_name"], "Sunrise Orchard")

    def test_add_farm_validation_errors(self):
        # Missing farm_name
        resp = self.client.post("/api/farms", headers=self.headers1, data=json.dumps({
            "location": "Nashik", "total_area": 10, "area_unit": "acre"
        }))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Farm name is required", resp.get_json()["message"])

        # Non-positive area
        resp = self.client.post("/api/farms", headers=self.headers1, data=json.dumps({
            "farm_name": "My Farm", "location": "Nashik", "total_area": -5, "area_unit": "acre"
        }))
        self.assertEqual(resp.status_code, 400)

        # Invalid unit
        resp = self.client.post("/api/farms", headers=self.headers1, data=json.dumps({
            "farm_name": "My Farm", "location": "Nashik", "total_area": 10, "area_unit": "sqft"
        }))
        self.assertEqual(resp.status_code, 400)

    def test_edit_farm_success(self):
        add_resp = self.client.post("/api/farms", headers=self.headers1, data=json.dumps({
            "farm_name": "Old Farm Name", "location": "Pune", "total_area": 8.0, "area_unit": "acre"
        }))
        farm_id = add_resp.get_json()["farm"]["id"]

        update_resp = self.client.put(f"/api/farms/{farm_id}", headers=self.headers1, data=json.dumps({
            "farm_name": "Updated Farm Name", "location": "Baramati", "total_area": 12.0, "area_unit": "hectare"
        }))
        self.assertEqual(update_resp.status_code, 200)
        updated = update_resp.get_json()["farm"]
        self.assertEqual(updated["farm_name"], "Updated Farm Name")
        self.assertEqual(updated["total_area"], 12.0)
        self.assertEqual(updated["area_unit"], "hectare")

    def test_delete_farm_success(self):
        add_resp = self.client.post("/api/farms", headers=self.headers1, data=json.dumps({
            "farm_name": "To Delete Farm", "location": "Pune", "total_area": 5.0, "area_unit": "acre"
        }))
        farm_id = add_resp.get_json()["farm"]["id"]

        del_resp = self.client.delete(f"/api/farms/{farm_id}", headers=self.headers1)
        self.assertEqual(del_resp.status_code, 200)

        get_resp = self.client.get(f"/api/farms/{farm_id}", headers=self.headers1)
        self.assertEqual(get_resp.status_code, 404)

    def test_farm_data_isolation(self):
        add_resp = self.client.post("/api/farms", headers=self.headers1, data=json.dumps({
            "farm_name": "User 1 Private Farm", "location": "Nagpur", "total_area": 20, "area_unit": "acre"
        }))
        farm_id = add_resp.get_json()["farm"]["id"]

        # User 2 cannot list User 1's farm
        u2_list = self.client.get("/api/farms", headers=self.headers2)
        self.assertEqual(u2_list.get_json()["count"], 0)

        # User 2 cannot get User 1's farm
        u2_get = self.client.get(f"/api/farms/{farm_id}", headers=self.headers2)
        self.assertEqual(u2_get.status_code, 404)

        # User 2 cannot edit User 1's farm
        u2_put = self.client.put(f"/api/farms/{farm_id}", headers=self.headers2, data=json.dumps({
            "farm_name": "Hacked", "location": "Unknown", "total_area": 1, "area_unit": "acre"
        }))
        self.assertEqual(u2_put.status_code, 404)

        # User 2 cannot delete User 1's farm
        u2_del = self.client.delete(f"/api/farms/{farm_id}", headers=self.headers2)
        self.assertEqual(u2_del.status_code, 404)

    # =========================================================================
    # CROPS & GROWTH TRACKING TESTS
    # =========================================================================

    def _create_farm_for_user1(self):
        resp = self.client.post("/api/farms", headers=self.headers1, data=json.dumps({
            "farm_name": "Main Valley Farm", "location": "Kolhapur", "total_area": 25.0, "area_unit": "acre"
        }))
        return resp.get_json()["farm"]["id"]

    def test_add_crop_success(self):
        farm_id = self._create_farm_for_user1()
        payload = {
            "farm_id": farm_id,
            "crop_name": "Sugarcane",
            "variety": "Co 86032",
            "planting_date": "2026-06-01",
            "cultivated_area": 10.0,
            "area_unit": "acre",
            "expected_harvest_date": "2027-04-15",
            "growth_status": "Growing",
            "notes": "Healthy tillering stage"
        }
        resp = self.client.post("/api/crops", headers=self.headers1, data=json.dumps(payload))
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertEqual(data["status"], "success")
        crop = data["crop"]
        self.assertEqual(crop["crop_name"], "Sugarcane")
        self.assertEqual(crop["variety"], "Co 86032")
        self.assertEqual(crop["farm_name"], "Main Valley Farm")
        self.assertEqual(crop["growth_status"], "Growing")
        self.assertGreater(crop["days_since_planting"], 0)

    def test_add_crop_cannot_use_another_users_farm(self):
        farm_id = self._create_farm_for_user1()
        payload = {
            "farm_id": farm_id,
            "crop_name": "Rice",
            "planting_date": "2026-07-01",
            "cultivated_area": 3.0,
            "area_unit": "acre"
        }
        resp = self.client.post("/api/crops", headers=self.headers2, data=json.dumps(payload))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Selected farm not found or does not belong to you", resp.get_json()["message"])

    def test_update_crop_growth_status_manually(self):
        farm_id = self._create_farm_for_user1()
        add_resp = self.client.post("/api/crops", headers=self.headers1, data=json.dumps({
            "farm_id": farm_id,
            "crop_name": "Tomato",
            "planting_date": "2026-09-01",
            "cultivated_area": 2.5,
            "area_unit": "acre",
            "growth_status": "Newly Planted"
        }))
        crop_id = add_resp.get_json()["crop"]["id"]

        # Valid stage progression
        for stage in ["Growing", "Flowering", "Fruiting", "Ready for Harvest", "Harvested"]:
            patch_resp = self.client.patch(f"/api/crops/{crop_id}/status", headers=self.headers1, data=json.dumps({
                "growth_status": stage
            }))
            self.assertEqual(patch_resp.status_code, 200)
            self.assertEqual(patch_resp.get_json()["growth_status"], stage)

        # Invalid stage rejected
        bad_resp = self.client.patch(f"/api/crops/{crop_id}/status", headers=self.headers1, data=json.dumps({
            "growth_status": "Unknown Stage"
        }))
        self.assertEqual(bad_resp.status_code, 400)

    def test_delete_crop(self):
        farm_id = self._create_farm_for_user1()
        add_resp = self.client.post("/api/crops", headers=self.headers1, data=json.dumps({
            "farm_id": farm_id,
            "crop_name": "Cotton",
            "planting_date": "2026-05-10",
            "cultivated_area": 4.0,
            "area_unit": "acre"
        }))
        crop_id = add_resp.get_json()["crop"]["id"]

        del_resp = self.client.delete(f"/api/crops/{crop_id}", headers=self.headers1)
        self.assertEqual(del_resp.status_code, 200)

        get_resp = self.client.get(f"/api/crops/{crop_id}", headers=self.headers1)
        self.assertEqual(get_resp.status_code, 404)

    # =========================================================================
    # DASHBOARD SUMMARY TESTS
    # =========================================================================

    def test_dashboard_summary(self):
        farm_id = self._create_farm_for_user1()

        # Add 3 crops with various statuses
        self.client.post("/api/crops", headers=self.headers1, data=json.dumps({
            "farm_id": farm_id, "crop_name": "Corn", "planting_date": "2026-08-01",
            "cultivated_area": 3.0, "area_unit": "acre", "growth_status": "Growing"
        }))
        self.client.post("/api/crops", headers=self.headers1, data=json.dumps({
            "farm_id": farm_id, "crop_name": "Chili", "planting_date": "2026-07-15",
            "cultivated_area": 1.5, "area_unit": "acre", "growth_status": "Flowering"
        }))
        self.client.post("/api/crops", headers=self.headers1, data=json.dumps({
            "farm_id": farm_id, "crop_name": "Soybean", "planting_date": "2026-06-10",
            "cultivated_area": 5.0, "area_unit": "acre", "growth_status": "Ready for Harvest"
        }))

        resp = self.client.get("/api/crops/dashboard-summary", headers=self.headers1)
        self.assertEqual(resp.status_code, 200)
        summary = resp.get_json()["summary"]
        self.assertEqual(summary["total_farms"], 1)
        self.assertEqual(summary["total_crops"], 3)
        self.assertEqual(summary["crops_growing"], 2)  # Growing + Flowering
        self.assertEqual(summary["crops_ready_for_harvest"], 1)

    # =========================================================================
    # AUTHENTICATION GUARD TESTS
    # =========================================================================

    def test_unauthenticated_requests_blocked(self):
        self.assertEqual(self.client.get("/api/farms").status_code, 401)
        self.assertEqual(self.client.post("/api/farms", data=json.dumps({})).status_code, 401)
        self.assertEqual(self.client.get("/api/crops").status_code, 401)
        self.assertEqual(self.client.post("/api/crops", data=json.dumps({})).status_code, 401)
        self.assertEqual(self.client.get("/api/crops/dashboard-summary").status_code, 401)


if __name__ == "__main__":
    unittest.main()
