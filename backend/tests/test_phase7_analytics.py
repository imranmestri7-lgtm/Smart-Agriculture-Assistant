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


class MockAnalyticsCursor:
    def __init__(self, farms, crops, diagnoses, irrigations):
        self.farms = farms
        self.crops = crops
        self.diagnoses = diagnoses
        self.irrigations = irrigations
        self._current_result = None

    def execute(self, query, params=None):
        clean_q = " ".join(query.split()).upper()
        params = list(params) if params else []

        # -------------------------------------------------------------
        # Filter options
        # -------------------------------------------------------------
        if "FROM FARMS WHERE USER_ID = %S ORDER BY FARM_NAME ASC" in clean_q:
            user_id = params[0]
            res = [
                {"id": f["id"], "farm_name": f["farm_name"]}
                for f in self.farms
                if f.get("user_id") == user_id
            ]
            res.sort(key=lambda x: x["farm_name"])
            self._current_result = res

        elif "SELECT DISTINCT CROP_NAME FROM CROPS WHERE USER_ID = %S AND CROP_NAME IS NOT NULL" in clean_q:
            user_id = params[0]
            res = [
                {"crop_name": c["crop_name"]}
                for c in self.crops
                if c.get("user_id") == user_id and c.get("crop_name")
            ]
            self._current_result = res

        elif "SELECT DISTINCT CROP FROM IRRIGATION_HISTORY WHERE USER_ID = %S AND CROP IS NOT NULL" in clean_q:
            user_id = params[0]
            res = [
                {"crop": i["crop"]}
                for i in self.irrigations
                if i.get("user_id") == user_id and i.get("crop")
            ]
            self._current_result = res

        # -------------------------------------------------------------
        # Summary Counts
        # -------------------------------------------------------------
        elif "SELECT COUNT(*) AS CNT FROM FARMS WHERE USER_ID = %S" in clean_q:
            user_id = params[0]
            cnt = sum(1 for f in self.farms if f.get("user_id") == user_id)
            self._current_result = [{"cnt": cnt}]

        elif "SELECT COUNT(*) AS CNT FROM CROPS WHERE USER_ID = %S AND GROWTH_STATUS IN ('GROWING', 'FLOWERING', 'FRUITING')" in clean_q:
            user_id = params[0]
            cnt = sum(1 for c in self.crops if c.get("user_id") == user_id and c.get("growth_status") in ("Growing", "Flowering", "Fruiting"))
            self._current_result = [{"cnt": cnt}]

        elif "SELECT COUNT(*) AS CNT FROM CROPS WHERE USER_ID = %S AND GROWTH_STATUS = 'READY FOR HARVEST'" in clean_q:
            user_id = params[0]
            cnt = sum(1 for c in self.crops if c.get("user_id") == user_id and c.get("growth_status") == "Ready for Harvest")
            self._current_result = [{"cnt": cnt}]

        elif "SELECT COUNT(*) AS CNT FROM CROPS WHERE USER_ID = %S" in clean_q:
            user_id = params[0]
            cnt = sum(1 for c in self.crops if c.get("user_id") == user_id)
            self._current_result = [{"cnt": cnt}]

        elif "SELECT COUNT(*) AS CNT FROM DIAGNOSIS_HISTORY WHERE USER_ID = %S" in clean_q:
            user_id = params[0]
            cnt = sum(1 for d in self.diagnoses if d.get("user_id") == user_id)
            self._current_result = [{"cnt": cnt}]

        elif "SELECT COUNT(*) AS CNT FROM IRRIGATION_HISTORY WHERE USER_ID = %S" in clean_q:
            user_id = params[0]
            cnt = sum(1 for i in self.irrigations if i.get("user_id") == user_id)
            self._current_result = [{"cnt": cnt}]

        # -------------------------------------------------------------
        # Crop Distribution by name
        # -------------------------------------------------------------
        elif "SELECT C.CROP_NAME, COUNT(*) AS COUNT, COALESCE(SUM(C.CULTIVATED_AREA), 0) AS TOTAL_AREA, MAX(C.AREA_UNIT) AS AREA_UNIT FROM CROPS C" in clean_q:
            matched_crops = self._filter_crops(params)
            group_dict = {}
            for c in matched_crops:
                name = c.get("crop_name")
                if name not in group_dict:
                    group_dict[name] = {"count": 0, "total_area": 0.0, "area_unit": c.get("area_unit") or "acre"}
                group_dict[name]["count"] += 1
                group_dict[name]["total_area"] += float(c.get("cultivated_area") or 0.0)
            res = [
                {"crop_name": k, "count": v["count"], "total_area": v["total_area"], "area_unit": v["area_unit"]}
                for k, v in group_dict.items()
            ]
            res.sort(key=lambda x: x["count"], reverse=True)
            self._current_result = res

        # -------------------------------------------------------------
        # Crop Growth Stage distribution
        # -------------------------------------------------------------
        elif "SELECT C.GROWTH_STATUS, COUNT(*) AS COUNT FROM CROPS C" in clean_q:
            matched_crops = self._filter_crops(params)
            group_dict = {}
            for c in matched_crops:
                st = c.get("growth_status")
                group_dict[st] = group_dict.get(st, 0) + 1
            res = [{"growth_status": k, "count": v} for k, v in group_dict.items()]
            self._current_result = res

        # -------------------------------------------------------------
        # Crops per Farm
        # -------------------------------------------------------------
        elif "COUNT(C.ID) AS COUNT FROM CROPS C LEFT JOIN FARMS F ON F.ID = C.FARM_ID" in clean_q:
            matched_crops = self._filter_crops(params)
            farm_name_map = {f["id"]: f["farm_name"] for f in self.farms}
            group_dict = {}
            for c in matched_crops:
                fid = c.get("farm_id")
                fname = farm_name_map.get(fid, "Unassigned")
                key = (fid, fname)
                group_dict[key] = group_dict.get(key, 0) + 1
            res = [
                {"farm_id": k[0], "farm_name": k[1], "count": v}
                for k, v in group_dict.items()
            ]
            res.sort(key=lambda x: x["count"], reverse=True)
            self._current_result = res

        # -------------------------------------------------------------
        # Crop Timeline
        # -------------------------------------------------------------
        elif "EXPECTED_HARVEST_DATE, C.GROWTH_STATUS, C.CULTIVATED_AREA, C.AREA_UNIT FROM CROPS C LEFT JOIN FARMS F" in clean_q:
            matched_crops = self._filter_crops(params)
            farm_name_map = {f["id"]: f["farm_name"] for f in self.farms}
            res = []
            for c in matched_crops:
                fid = c.get("farm_id")
                res.append({
                    "id": c["id"],
                    "crop_name": c["crop_name"],
                    "variety": c.get("variety"),
                    "farm_name": farm_name_map.get(fid, "Unassigned"),
                    "planting_date": c.get("planting_date"),
                    "expected_harvest_date": c.get("expected_harvest_date"),
                    "growth_status": c.get("growth_status"),
                    "cultivated_area": c.get("cultivated_area"),
                    "area_unit": c.get("area_unit")
                })
            # sort by planting_date DESC
            res.sort(key=lambda x: str(x.get("planting_date") or ""), reverse=True)
            self._current_result = res[:20]

        # -------------------------------------------------------------
        # Diagnosis History Analytics
        # -------------------------------------------------------------
        elif "FROM DIAGNOSIS_HISTORY DH" in clean_q:
            matched_diag = self._filter_diagnoses(params, clean_q)
            res = [
                {
                    "predicted_class": d["predicted_class"],
                    "confidence": d.get("confidence"),
                    "diagnosis_date": d.get("diagnosis_date")
                }
                for d in matched_diag
            ]
            self._current_result = res

        # -------------------------------------------------------------
        # Irrigation History Analytics
        # -------------------------------------------------------------
        elif "FROM IRRIGATION_HISTORY IH" in clean_q:
            matched_irrig = self._filter_irrigations(params, clean_q)
            res = [
                {
                    "crop": i.get("crop"),
                    "soil_moisture": i.get("soil_moisture"),
                    "is_irrigation_needed": i.get("is_irrigation_needed"),
                    "water_quantity_mm": i.get("water_quantity_mm"),
                    "recommendation_status": i.get("recommendation_status"),
                    "created_at": i.get("created_at")
                }
                for i in matched_irrig
            ]
            self._current_result = res

        else:
            self._current_result = []

    def _filter_crops(self, params):
        if not params:
            return []
        user_id = params[0]
        crops = [c for c in self.crops if c.get("user_id") == user_id]
        idx = 1
        # Check optional params passed in order: farm_id, crop_name, start_date, end_date
        while idx < len(params):
            val = params[idx]
            if isinstance(val, int):
                crops = [c for c in crops if c.get("farm_id") == val]
            elif isinstance(val, str) and not isinstance(val, (date, datetime)) and len(val) != 10:
                crops = [c for c in crops if c.get("crop_name") == val]
            elif isinstance(val, (date, datetime)) or (isinstance(val, str) and len(val) == 10):
                # date filter
                d_val = val if isinstance(val, date) else datetime.strptime(val[:10], "%Y-%m-%d").date()
                if idx == 1 or (idx > 1 and not isinstance(params[idx-1], (date, datetime))):
                    crops = [c for c in crops if c.get("planting_date") and (c["planting_date"] if isinstance(c["planting_date"], date) else datetime.strptime(str(c["planting_date"])[:10], "%Y-%m-%d").date()) >= d_val]
                else:
                    crops = [c for c in crops if c.get("planting_date") and (c["planting_date"] if isinstance(c["planting_date"], date) else datetime.strptime(str(c["planting_date"])[:10], "%Y-%m-%d").date()) <= d_val]
            idx += 1
        return crops

    def _filter_diagnoses(self, params, query):
        user_id = params[0]
        diags = [d for d in self.diagnoses if d.get("user_id") == user_id]
        for p in params[1:]:
            if isinstance(p, str) and "%" in p:
                kw = p.replace("%", "").lower()
                diags = [d for d in diags if kw in (d.get("predicted_class") or "").lower()]
            elif isinstance(p, (date, datetime)) or (isinstance(p, str) and len(p) == 10):
                d_val = p if isinstance(p, date) else datetime.strptime(p[:10], "%Y-%m-%d").date()
                if ">=" in query:
                    diags = [d for d in diags if d.get("diagnosis_date") and (d["diagnosis_date"] if isinstance(d["diagnosis_date"], date) else datetime.strptime(str(d["diagnosis_date"])[:10], "%Y-%m-%d").date()) >= d_val]
                elif "<=" in query:
                    diags = [d for d in diags if d.get("diagnosis_date") and (d["diagnosis_date"] if isinstance(d["diagnosis_date"], date) else datetime.strptime(str(d["diagnosis_date"])[:10], "%Y-%m-%d").date()) <= d_val]
        return diags

    def _filter_irrigations(self, params, query):
        user_id = params[0]
        irrigs = [i for i in self.irrigations if i.get("user_id") == user_id]
        for p in params[1:]:
            if isinstance(p, str) and len(p) != 10:
                irrigs = [i for i in irrigs if (i.get("crop") or "").lower() == p.lower()]
            elif isinstance(p, (date, datetime)) or (isinstance(p, str) and len(p) == 10):
                d_val = p if isinstance(p, date) else datetime.strptime(p[:10], "%Y-%m-%d").date()
                if ">=" in query:
                    irrigs = [i for i in irrigs if i.get("created_at") and (i["created_at"] if isinstance(i["created_at"], date) else datetime.strptime(str(i["created_at"])[:10], "%Y-%m-%d").date()) >= d_val]
                elif "<=" in query:
                    irrigs = [i for i in irrigs if i.get("created_at") and (i["created_at"] if isinstance(i["created_at"], date) else datetime.strptime(str(i["created_at"])[:10], "%Y-%m-%d").date()) <= d_val]
        return irrigs

    def fetchall(self):
        return self._current_result or []

    def fetchone(self):
        if self._current_result:
            return self._current_result[0]
        return None

    def close(self):
        pass


class MockAnalyticsConnection:
    def __init__(self, farms, crops, diagnoses, irrigations):
        self.farms = farms
        self.crops = crops
        self.diagnoses = diagnoses
        self.irrigations = irrigations

    def cursor(self, dictionary=True):
        return MockAnalyticsCursor(self.farms, self.crops, self.diagnoses, self.irrigations)

    def close(self):
        pass


class TestPhase7Analytics(unittest.TestCase):
    def setUp(self):
        self.client = flask_app.test_client()
        self.user1_id = 101
        self.user2_id = 102
        self.user1_token = create_access_token(self.user1_id)
        self.user2_token = create_access_token(self.user2_id)

        self.farms_data = [
            {"id": 1, "user_id": 101, "farm_name": "Green Valley"},
            {"id": 2, "user_id": 101, "farm_name": "Sunrise Farm"},
            {"id": 3, "user_id": 102, "farm_name": "Other Farmer Farm"},
        ]

        self.crops_data = [
            {
                "id": 1,
                "user_id": 101,
                "farm_id": 1,
                "crop_name": "Wheat",
                "variety": "Lokwan",
                "planting_date": date(2026, 1, 10),
                "expected_harvest_date": date(2026, 4, 20),
                "growth_status": "Growing",
                "cultivated_area": 4.5,
                "area_unit": "acre"
            },
            {
                "id": 2,
                "user_id": 101,
                "farm_id": 1,
                "crop_name": "Tomato",
                "variety": "Roma",
                "planting_date": date(2026, 2, 1),
                "expected_harvest_date": date(2026, 5, 1),
                "growth_status": "Flowering",
                "cultivated_area": 2.0,
                "area_unit": "acre"
            },
            {
                "id": 3,
                "user_id": 101,
                "farm_id": 2,
                "crop_name": "Rice",
                "variety": "Basmati",
                "planting_date": date(2026, 1, 5),
                "expected_harvest_date": date(2026, 4, 1),
                "growth_status": "Ready for Harvest",
                "cultivated_area": 3.0,
                "area_unit": "hectare"
            },
            {
                "id": 4,
                "user_id": 102,
                "farm_id": 3,
                "crop_name": "Cotton",
                "variety": "BT",
                "planting_date": date(2026, 2, 10),
                "expected_harvest_date": date(2026, 6, 10),
                "growth_status": "Growing",
                "cultivated_area": 10.0,
                "area_unit": "acre"
            }
        ]

        self.diagnoses_data = [
            {
                "id": 1,
                "user_id": 101,
                "predicted_class": "Tomato___Early_blight",
                "confidence": 92.5,
                "diagnosis_date": datetime(2026, 2, 15, 10, 0, 0)
            },
            {
                "id": 2,
                "user_id": 101,
                "predicted_class": "Tomato___healthy",
                "confidence": 98.0,
                "diagnosis_date": datetime(2026, 2, 18, 11, 0, 0)
            },
            {
                "id": 3,
                "user_id": 101,
                "predicted_class": "Wheat___Brown_rust",
                "confidence": 88.0,
                "diagnosis_date": datetime(2026, 2, 20, 9, 30, 0)
            },
            {
                "id": 4,
                "user_id": 102,
                "predicted_class": "Cotton___Boll_rot",
                "confidence": 95.0,
                "diagnosis_date": datetime(2026, 2, 22, 14, 0, 0)
            }
        ]

        self.irrigations_data = [
            {
                "id": 1,
                "user_id": 101,
                "crop": "Wheat",
                "soil_moisture": 30.5,
                "is_irrigation_needed": 1,
                "water_quantity_mm": 25.0,
                "recommendation_status": "Irrigation Recommended",
                "created_at": datetime(2026, 2, 12, 8, 0, 0)
            },
            {
                "id": 2,
                "user_id": 101,
                "crop": "Tomato",
                "soil_moisture": 65.0,
                "is_irrigation_needed": 0,
                "water_quantity_mm": 0.0,
                "recommendation_status": "Sufficient Moisture",
                "created_at": datetime(2026, 2, 16, 9, 0, 0)
            },
            {
                "id": 3,
                "user_id": 102,
                "crop": "Cotton",
                "soil_moisture": 25.0,
                "is_irrigation_needed": 1,
                "water_quantity_mm": 40.0,
                "recommendation_status": "Irrigation Recommended",
                "created_at": datetime(2026, 2, 20, 7, 0, 0)
            }
        ]

    def _get_mock_conn(self):
        return MockAnalyticsConnection(
            self.farms_data, self.crops_data, self.diagnoses_data, self.irrigations_data
        )

    # -------------------------------------------------------------
    # 1. AUTHENTICATION & ACCESS CONTROL TESTS
    # -------------------------------------------------------------
    def test_filter_options_unauthorized_no_token(self):
        resp = self.client.get("/api/analytics/filter-options")
        self.assertEqual(resp.status_code, 401)
        data = json.loads(resp.data)
        self.assertEqual(data["status"], "error")

    def test_filter_options_unauthorized_invalid_token(self):
        resp = self.client.get("/api/analytics/filter-options", headers={"Authorization": "Bearer invalid.fake.token"})
        self.assertEqual(resp.status_code, 401)

    def test_overview_unauthorized_no_token(self):
        resp = self.client.get("/api/analytics/overview")
        self.assertEqual(resp.status_code, 401)

    # -------------------------------------------------------------
    # 2. FILTER OPTIONS ENDPOINT
    # -------------------------------------------------------------
    @patch("routes.analytics_routes.get_db_connection")
    def test_filter_options_returns_user_data(self, mock_db):
        mock_db.return_value = self._get_mock_conn()

        resp = self.client.get(
            "/api/analytics/filter-options",
            headers={"Authorization": f"Bearer {self.user1_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["status"], "success")

        # Must have farms for user1 only
        farm_names = [f["farm_name"] for f in data["farms"]]
        self.assertIn("Green Valley", farm_names)
        self.assertIn("Sunrise Farm", farm_names)
        self.assertNotIn("Other Farmer Farm", farm_names)

        # Must have distinct crops
        crops = data["crops"]
        self.assertIn("Wheat", crops)
        self.assertIn("Tomato", crops)
        self.assertIn("Rice", crops)
        self.assertNotIn("Cotton", crops)

    # -------------------------------------------------------------
    # 3. OVERVIEW WITH POPULATED DATA
    # -------------------------------------------------------------
    @patch("routes.analytics_routes.get_db_connection")
    def test_overview_populated_metrics(self, mock_db):
        mock_db.return_value = self._get_mock_conn()

        resp = self.client.get(
            "/api/analytics/overview",
            headers={"Authorization": f"Bearer {self.user1_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["status"], "success")

        # Summary check
        summary = data["summary"]
        self.assertEqual(summary["total_farms"], 2)
        self.assertEqual(summary["total_crops"], 3)
        self.assertEqual(summary["total_diagnoses"], 3)
        self.assertEqual(summary["total_irrigations"], 2)
        self.assertEqual(summary["crops_growing"], 2)  # Growing + Flowering
        self.assertEqual(summary["crops_ready_for_harvest"], 1)

        # Crop Analytics check
        crop_analytics = data["crop_analytics"]
        crop_names = [c["crop_name"] for c in crop_analytics["crops_by_name"]]
        self.assertIn("Wheat", crop_names)
        self.assertIn("Tomato", crop_names)

        stages = {s["stage"]: s["count"] for s in crop_analytics["growth_stages"]}
        self.assertEqual(stages["Growing"], 1)
        self.assertEqual(stages["Flowering"], 1)
        self.assertEqual(stages["Ready for Harvest"], 1)
        self.assertEqual(stages["Harvested"], 0)

        timeline = crop_analytics["timeline"]
        self.assertEqual(len(timeline), 3)

        # Disease Analytics check
        disease_analytics = data["disease_analytics"]
        self.assertEqual(disease_analytics["total_diagnoses"], 3)
        self.assertEqual(disease_analytics["healthy_count"], 1)
        self.assertEqual(disease_analytics["diseased_count"], 2)

        top_disease_names = [d["disease_name"] for d in disease_analytics["top_diseases"]]
        self.assertIn("Early Blight", top_disease_names)
        self.assertIn("Brown Rust", top_disease_names)

        # Irrigation Analytics check
        irrig_analytics = data["irrigation_analytics"]
        self.assertEqual(irrig_analytics["total_recommendations"], 2)
        self.assertEqual(irrig_analytics["irrigation_needed_count"], 1)
        self.assertEqual(irrig_analytics["irrigation_not_needed_count"], 1)
        self.assertEqual(irrig_analytics["total_estimated_water_mm"], 25.0)

    # -------------------------------------------------------------
    # 4. OVERVIEW WITH EMPTY STATE (Zero records)
    # -------------------------------------------------------------
    @patch("routes.analytics_routes.get_db_connection")
    def test_overview_empty_farmer(self, mock_db):
        # Empty farmer 999
        empty_token = create_access_token(999)
        mock_db.return_value = MockAnalyticsConnection([], [], [], [])

        resp = self.client.get(
            "/api/analytics/overview",
            headers={"Authorization": f"Bearer {empty_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["status"], "success")

        summary = data["summary"]
        self.assertEqual(summary["total_farms"], 0)
        self.assertEqual(summary["total_crops"], 0)
        self.assertEqual(summary["total_diagnoses"], 0)
        self.assertEqual(summary["total_irrigations"], 0)
        self.assertEqual(summary["crops_growing"], 0)
        self.assertEqual(summary["crops_ready_for_harvest"], 0)

        self.assertEqual(data["crop_analytics"]["crops_by_name"], [])
        self.assertEqual(data["crop_analytics"]["timeline"], [])
        self.assertEqual(data["disease_analytics"]["total_diagnoses"], 0)
        self.assertEqual(data["disease_analytics"]["top_diseases"], [])
        self.assertEqual(data["irrigation_analytics"]["total_recommendations"], 0)
        self.assertEqual(data["irrigation_analytics"]["total_estimated_water_mm"], 0.0)

    # -------------------------------------------------------------
    # 5. INPUT VALIDATION & FILTERS
    # -------------------------------------------------------------
    @patch("routes.analytics_routes.get_db_connection")
    def test_invalid_farm_id_param(self, mock_db):
        resp = self.client.get(
            "/api/analytics/overview?farm_id=abc",
            headers={"Authorization": f"Bearer {self.user1_token}"}
        )
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertIn("Invalid farm_id", data["message"])

    @patch("routes.analytics_routes.get_db_connection")
    def test_invalid_date_format(self, mock_db):
        resp = self.client.get(
            "/api/analytics/overview?start_date=2026/02/01",
            headers={"Authorization": f"Bearer {self.user1_token}"}
        )
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertIn("Invalid start_date format", data["message"])

        resp2 = self.client.get(
            "/api/analytics/overview?end_date=not-a-date",
            headers={"Authorization": f"Bearer {self.user1_token}"}
        )
        self.assertEqual(resp2.status_code, 400)
        data2 = json.loads(resp2.data)
        self.assertIn("Invalid end_date format", data2["message"])

    # -------------------------------------------------------------
    # 6. FARMER DATA ISOLATION
    # -------------------------------------------------------------
    @patch("routes.analytics_routes.get_db_connection")
    def test_farmer_data_isolation(self, mock_db):
        mock_db.return_value = self._get_mock_conn()

        # Farmer 2 checks overview
        resp = self.client.get(
            "/api/analytics/overview",
            headers={"Authorization": f"Bearer {self.user2_token}"}
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)

        # Farmer 2 has only 1 farm, 1 crop, 1 diagnosis, 1 irrigation
        self.assertEqual(data["summary"]["total_farms"], 1)
        self.assertEqual(data["summary"]["total_crops"], 1)
        self.assertEqual(data["summary"]["total_diagnoses"], 1)
        self.assertEqual(data["summary"]["total_irrigations"], 1)

        # The crop must be Cotton only
        crop_names = [c["crop_name"] for c in data["crop_analytics"]["crops_by_name"]]
        self.assertEqual(crop_names, ["Cotton"])


if __name__ == "__main__":
    unittest.main()
