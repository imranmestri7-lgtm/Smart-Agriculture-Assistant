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


class MockFinancialCursor:
    def __init__(self, expenses, harvests, crops, farms):
        self.expenses = expenses
        self.harvests = harvests
        self.crops = crops
        self.farms = farms
        self.lastrowid = None
        self.rowcount = 0
        self._current_result = None

    def execute(self, query, params=None):
        clean_q = " ".join(query.split()).upper()
        params = list(params) if params else []

        # -------------------------------------------------------------
        # Context Crops & Farms
        # -------------------------------------------------------------
        if "FROM CROPS WHERE USER_ID = %S" in clean_q and "SELECT" in clean_q:
            uid = int(params[0])
            res = [c for c in self.crops if int(c["user_id"]) == uid]
            self._current_result = res

        elif "FROM FARMS WHERE USER_ID = %S" in clean_q and "SELECT" in clean_q:
            uid = int(params[0])
            res = [f for f in self.farms if int(f["user_id"]) == uid]
            self._current_result = res

        elif "FROM CROPS WHERE ID = %S AND USER_ID = %S" in clean_q:
            cid = int(params[0])
            uid = int(params[1])
            res = [c for c in self.crops if int(c["id"]) == cid and int(c["user_id"]) == uid]
            self._current_result = res

        elif "FROM FARMS WHERE ID = %S AND USER_ID = %S" in clean_q:
            fid = int(params[0])
            uid = int(params[1])
            res = [f for f in self.farms if int(f["id"]) == fid and int(f["user_id"]) == uid]
            self._current_result = res

        # -------------------------------------------------------------
        # Expenses INSERT
        # -------------------------------------------------------------
        elif "INSERT INTO FARM_EXPENSES" in clean_q:
            new_id = (max([e["id"] for e in self.expenses], default=0)) + 1
            # (user_id, farm_id, crop_id, crop_name, category, amount, expense_date, quantity, unit, description, notes)
            new_exp = {
                "id": new_id,
                "user_id": int(params[0]),
                "farm_id": int(params[1]) if params[1] is not None else None,
                "crop_id": int(params[2]) if params[2] is not None else None,
                "crop_name": params[3],
                "category": params[4],
                "amount": float(params[5]),
                "expense_date": params[6],
                "quantity": float(params[7]) if params[7] is not None else None,
                "unit": params[8],
                "description": params[9],
                "notes": params[10],
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            self.expenses.append(new_exp)
            self.lastrowid = new_id
            self.rowcount = 1
            self._current_result = []

        # -------------------------------------------------------------
        # Expenses UPDATE
        # -------------------------------------------------------------
        elif "UPDATE FARM_EXPENSES" in clean_q:
            # SET farm_id = %s, crop_id = %s, crop_name = %s, category = %s, amount = %s, expense_date = %s, quantity = %s, unit = %s, description = %s, notes = %s WHERE id = %s AND user_id = %s
            eid = int(params[10])
            uid = int(params[11])
            cnt = 0
            for e in self.expenses:
                if int(e["id"]) == eid and int(e["user_id"]) == uid:
                    e["farm_id"] = int(params[0]) if params[0] is not None else None
                    e["crop_id"] = int(params[1]) if params[1] is not None else None
                    e["crop_name"] = params[2]
                    e["category"] = params[3]
                    e["amount"] = float(params[4])
                    e["expense_date"] = params[5]
                    e["quantity"] = float(params[6]) if params[6] is not None else None
                    e["unit"] = params[7]
                    e["description"] = params[8]
                    e["notes"] = params[9]
                    e["updated_at"] = datetime.now()
                    cnt += 1
            self.rowcount = cnt
            self._current_result = []

        # -------------------------------------------------------------
        # Expenses DELETE
        # -------------------------------------------------------------
        elif "DELETE FROM FARM_EXPENSES WHERE ID = %S AND USER_ID = %S" in clean_q:
            eid = int(params[0])
            uid = int(params[1])
            before = len(self.expenses)
            self.expenses[:] = [e for e in self.expenses if not (int(e["id"]) == eid and int(e["user_id"]) == uid)]
            self.rowcount = before - len(self.expenses)
            self._current_result = []

        # -------------------------------------------------------------
        # Expenses SELECT SINGLE / EXISTENCE
        # -------------------------------------------------------------
        elif "SELECT ID FROM FARM_EXPENSES WHERE ID = %S AND USER_ID = %S" in clean_q:
            eid = int(params[0])
            uid = int(params[1])
            res = [e for e in self.expenses if int(e["id"]) == eid and int(e["user_id"]) == uid]
            self._current_result = [{"id": res[0]["id"]}] if res else []

        elif "FROM FARM_EXPENSES E" in clean_q and "WHERE E.ID = %S AND E.USER_ID = %S" in clean_q:
            eid = int(params[0])
            uid = int(params[1])
            res = [e for e in self.expenses if int(e["id"]) == eid and int(e["user_id"]) == uid]
            if res:
                item = dict(res[0])
                farm = next((f for f in self.farms if f["id"] == item.get("farm_id")), None)
                crop = next((c for c in self.crops if c["id"] == item.get("crop_id")), None)
                item["farm_name"] = farm["farm_name"] if farm else None
                item["variety"] = crop.get("variety") if crop else None
                self._current_result = [item]
            else:
                self._current_result = []

        # -------------------------------------------------------------
        # Expenses COUNT & LIST
        # -------------------------------------------------------------
        elif "SELECT COUNT(*) AS TOTAL_COUNT, COALESCE(SUM(AMOUNT), 0) AS TOTAL_AMOUNT FROM FARM_EXPENSES" in clean_q:
            uid = int(params[0])
            matched = [e for e in self.expenses if int(e["user_id"]) == uid]
            tot_amt = sum(e["amount"] for e in matched)
            self._current_result = [{"total_count": len(matched), "total_amount": tot_amt}]

        elif "FROM FARM_EXPENSES E" in clean_q and "ORDER BY E.EXPENSE_DATE DESC" in clean_q:
            uid = int(params[0])
            matched = [e for e in self.expenses if int(e["user_id"]) == uid]
            matched.sort(key=lambda x: str(x.get("expense_date") or ""), reverse=True)
            res = []
            for item in matched:
                d = dict(item)
                farm = next((f for f in self.farms if f["id"] == d.get("farm_id")), None)
                crop = next((c for c in self.crops if c["id"] == d.get("crop_id")), None)
                d["farm_name"] = farm["farm_name"] if farm else None
                d["variety"] = crop.get("variety") if crop else None
                res.append(d)
            self._current_result = res

        # -------------------------------------------------------------
        # Harvests INSERT
        # -------------------------------------------------------------
        elif "INSERT INTO FARM_HARVESTS" in clean_q:
            new_id = (max([h["id"] for h in self.harvests], default=0)) + 1
            # (user_id, farm_id, crop_id, crop_name, harvest_date, quantity, unit, price_per_unit, total_revenue, buyer_name, notes)
            new_harv = {
                "id": new_id,
                "user_id": int(params[0]),
                "farm_id": int(params[1]) if params[1] is not None else None,
                "crop_id": int(params[2]) if params[2] is not None else None,
                "crop_name": params[3],
                "harvest_date": params[4],
                "quantity": float(params[5]),
                "unit": params[6],
                "price_per_unit": float(params[7]),
                "total_revenue": float(params[8]),
                "buyer_name": params[9],
                "notes": params[10],
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            self.harvests.append(new_harv)
            self.lastrowid = new_id
            self.rowcount = 1
            self._current_result = []

        # -------------------------------------------------------------
        # Harvests UPDATE
        # -------------------------------------------------------------
        elif "UPDATE FARM_HARVESTS" in clean_q:
            hid = int(params[10])
            uid = int(params[11])
            cnt = 0
            for h in self.harvests:
                if int(h["id"]) == hid and int(h["user_id"]) == uid:
                    h["farm_id"] = int(params[0]) if params[0] is not None else None
                    h["crop_id"] = int(params[1]) if params[1] is not None else None
                    h["crop_name"] = params[2]
                    h["harvest_date"] = params[3]
                    h["quantity"] = float(params[4])
                    h["unit"] = params[5]
                    h["price_per_unit"] = float(params[6])
                    h["total_revenue"] = float(params[7])
                    h["buyer_name"] = params[8]
                    h["notes"] = params[9]
                    h["updated_at"] = datetime.now()
                    cnt += 1
            self.rowcount = cnt
            self._current_result = []

        # -------------------------------------------------------------
        # Harvests DELETE
        # -------------------------------------------------------------
        elif "DELETE FROM FARM_HARVESTS WHERE ID = %S AND USER_ID = %S" in clean_q:
            hid = int(params[0])
            uid = int(params[1])
            before = len(self.harvests)
            self.harvests[:] = [h for h in self.harvests if not (int(h["id"]) == hid and int(h["user_id"]) == uid)]
            self.rowcount = before - len(self.harvests)
            self._current_result = []

        # -------------------------------------------------------------
        # Harvests SELECT SINGLE / EXISTENCE
        # -------------------------------------------------------------
        elif "SELECT ID FROM FARM_HARVESTS WHERE ID = %S AND USER_ID = %S" in clean_q:
            hid = int(params[0])
            uid = int(params[1])
            res = [h for h in self.harvests if int(h["id"]) == hid and int(h["user_id"]) == uid]
            self._current_result = [{"id": res[0]["id"]}] if res else []

        elif "FROM FARM_HARVESTS H" in clean_q and "WHERE H.ID = %S AND H.USER_ID = %S" in clean_q:
            hid = int(params[0])
            uid = int(params[1])
            res = [h for h in self.harvests if int(h["id"]) == hid and int(h["user_id"]) == uid]
            if res:
                item = dict(res[0])
                farm = next((f for f in self.farms if f["id"] == item.get("farm_id")), None)
                crop = next((c for c in self.crops if c["id"] == item.get("crop_id")), None)
                item["farm_name"] = farm["farm_name"] if farm else None
                item["variety"] = crop.get("variety") if crop else None
                self._current_result = [item]
            else:
                self._current_result = []

        # -------------------------------------------------------------
        # Harvests COUNT & LIST
        # -------------------------------------------------------------
        elif "SELECT COUNT(*) AS TOTAL_COUNT, COALESCE(SUM(TOTAL_REVENUE), 0) AS TOTAL_REVENUE, COALESCE(SUM(QUANTITY), 0) AS TOTAL_QUANTITY FROM FARM_HARVESTS" in clean_q:
            uid = int(params[0])
            matched = [h for h in self.harvests if int(h["user_id"]) == uid]
            tot_rev = sum(h["total_revenue"] for h in matched)
            tot_qty = sum(h["quantity"] for h in matched)
            self._current_result = [{"total_count": len(matched), "total_revenue": tot_rev, "total_quantity": tot_qty}]

        elif "FROM FARM_HARVESTS H" in clean_q and "ORDER BY H.HARVEST_DATE DESC" in clean_q:
            uid = int(params[0])
            matched = [h for h in self.harvests if int(h["user_id"]) == uid]
            matched.sort(key=lambda x: str(x.get("harvest_date") or ""), reverse=True)
            res = []
            for item in matched:
                d = dict(item)
                farm = next((f for f in self.farms if f["id"] == d.get("farm_id")), None)
                crop = next((c for c in self.crops if c["id"] == d.get("crop_id")), None)
                d["farm_name"] = farm["farm_name"] if farm else None
                d["variety"] = crop.get("variety") if crop else None
                res.append(d)
            self._current_result = res

        # -------------------------------------------------------------
        # FINANCIAL SUMMARY AGGREGATIONS
        # -------------------------------------------------------------
        elif "SELECT COALESCE(SUM(AMOUNT), 0) AS TOTAL_EXPENSES, COUNT(*) AS COUNT_EXPENSES FROM FARM_EXPENSES WHERE USER_ID = %S" in clean_q:
            uid = int(params[0])
            matched = [e for e in self.expenses if int(e["user_id"]) == uid]
            tot_exp = sum(e["amount"] for e in matched)
            self._current_result = [{"total_expenses": tot_exp, "count_expenses": len(matched)}]

        elif "SELECT COALESCE(SUM(TOTAL_REVENUE), 0) AS TOTAL_REVENUE, COALESCE(SUM(QUANTITY), 0) AS TOTAL_HARVESTED, COUNT(*) AS COUNT_HARVESTS FROM FARM_HARVESTS WHERE USER_ID = %S" in clean_q:
            uid = int(params[0])
            matched = [h for h in self.harvests if int(h["user_id"]) == uid]
            tot_rev = sum(h["total_revenue"] for h in matched)
            tot_qty = sum(h["quantity"] for h in matched)
            self._current_result = [{"total_revenue": tot_rev, "total_harvested": tot_qty, "count_harvests": len(matched)}]

        elif "CATEGORY, COALESCE(SUM(AMOUNT), 0) AS CATEGORY_TOTAL, COUNT(*) AS ITEMS_COUNT FROM FARM_EXPENSES WHERE USER_ID = %S GROUP BY CATEGORY" in clean_q:
            uid = int(params[0])
            matched = [e for e in self.expenses if int(e["user_id"]) == uid]
            cats = {}
            for e in matched:
                c = e["category"]
                if c not in cats:
                    cats[c] = {"category": c, "category_total": 0.0, "items_count": 0}
                cats[c]["category_total"] += e["amount"]
                cats[c]["items_count"] += 1
            res = list(cats.values())
            res.sort(key=lambda x: x["category_total"], reverse=True)
            self._current_result = res

        elif "FROM FARM_EXPENSES WHERE USER_ID = %S GROUP BY COALESCE(CROP_NAME, 'GENERAL FARM OVERHEAD')" in clean_q:
            uid = int(params[0])
            matched = [e for e in self.expenses if int(e["user_id"]) == uid]
            crops_m = {}
            for e in matched:
                cname = e.get("crop_name") or "General Farm Overhead"
                crops_m[cname] = crops_m.get(cname, 0.0) + e["amount"]
            self._current_result = [{"crop_name": k, "crop_expenses": v} for k, v in crops_m.items()]

        elif "FROM FARM_HARVESTS WHERE USER_ID = %S GROUP BY CROP_NAME" in clean_q:
            uid = int(params[0])
            matched = [h for h in self.harvests if int(h["user_id"]) == uid]
            crops_m = {}
            for h in matched:
                cname = h["crop_name"]
                if cname not in crops_m:
                    crops_m[cname] = {"crop_name": cname, "crop_revenue": 0.0, "crop_qty": 0.0}
                crops_m[cname]["crop_revenue"] += h["total_revenue"]
                crops_m[cname]["crop_qty"] += h["quantity"]
            self._current_result = list(crops_m.values())

        elif "DATE_FORMAT(EXPENSE_DATE, '%Y-%M') AS YM, COALESCE(SUM(AMOUNT), 0) AS MONTH_EXPENSES FROM FARM_EXPENSES WHERE USER_ID = %S" in clean_q:
            uid = int(params[0])
            matched = [e for e in self.expenses if int(e["user_id"]) == uid]
            yms = {}
            for e in matched:
                ym = str(e["expense_date"])[:7]
                yms[ym] = yms.get(ym, 0.0) + e["amount"]
            res = [{"ym": k, "month_expenses": v} for k, v in sorted(yms.items())]
            self._current_result = res

        elif "DATE_FORMAT(HARVEST_DATE, '%Y-%M') AS YM, COALESCE(SUM(TOTAL_REVENUE), 0) AS MONTH_REVENUE FROM FARM_HARVESTS WHERE USER_ID = %S" in clean_q:
            uid = int(params[0])
            matched = [h for h in self.harvests if int(h["user_id"]) == uid]
            yms = {}
            for h in matched:
                ym = str(h["harvest_date"])[:7]
                yms[ym] = yms.get(ym, 0.0) + h["total_revenue"]
            res = [{"ym": k, "month_revenue": v} for k, v in sorted(yms.items())]
            self._current_result = res

        elif "SELECT EXPENSE_DATE, AMOUNT FROM FARM_EXPENSES WHERE USER_ID = %S" in clean_q:
            uid = int(params[0])
            self._current_result = [{"expense_date": e["expense_date"], "amount": e["amount"]} for e in self.expenses if int(e["user_id"]) == uid]

        elif "SELECT HARVEST_DATE, TOTAL_REVENUE FROM FARM_HARVESTS WHERE USER_ID = %S" in clean_q:
            uid = int(params[0])
            self._current_result = [{"harvest_date": h["harvest_date"], "total_revenue": h["total_revenue"]} for h in self.harvests if int(h["user_id"]) == uid]

        elif "FROM FARM_EXPENSES E LEFT JOIN FARMS F ON F.ID = E.FARM_ID WHERE E.USER_ID = %S ORDER BY E.EXPENSE_DATE DESC, E.ID DESC LIMIT 5" in clean_q:
            uid = int(params[0])
            matched = [e for e in self.expenses if int(e["user_id"]) == uid]
            matched.sort(key=lambda x: str(x.get("expense_date") or ""), reverse=True)
            self._current_result = matched[:5]

        elif "FROM FARM_HARVESTS H LEFT JOIN FARMS F ON F.ID = H.FARM_ID WHERE H.USER_ID = %S ORDER BY H.HARVEST_DATE DESC, H.ID DESC LIMIT 5" in clean_q:
            uid = int(params[0])
            matched = [h for h in self.harvests if int(h["user_id"]) == uid]
            matched.sort(key=lambda x: str(x.get("harvest_date") or ""), reverse=True)
            self._current_result = matched[:5]

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


class MockFinancialConnection:
    def __init__(self, expenses, harvests, crops, farms):
        self.expenses = expenses
        self.harvests = harvests
        self.crops = crops
        self.farms = farms

    def cursor(self, dictionary=True):
        return MockFinancialCursor(self.expenses, self.harvests, self.crops, self.farms)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


class FinancialRoutesTestCase(unittest.TestCase):
    def setUp(self):
        self.client = flask_app.test_client()
        self.farmer1_id = 101
        self.farmer2_id = 202

        self.farmer1_token = create_access_token(self.farmer1_id)
        self.farmer2_token = create_access_token(self.farmer2_id)

        self.expenses = []
        self.harvests = []
        self.farms = [
            {"id": 1, "user_id": self.farmer1_id, "farm_name": "Sunrise Farm", "location": "Pune, Maharashtra"},
            {"id": 2, "user_id": self.farmer2_id, "farm_name": "Valley Agro", "location": "Nashik, Maharashtra"}
        ]
        self.crops = [
            {"id": 10, "user_id": self.farmer1_id, "farm_id": 1, "crop_name": "Wheat", "variety": "Sharbati", "planting_date": "2026-11-01"},
            {"id": 20, "user_id": self.farmer1_id, "farm_id": 1, "crop_name": "Tomato", "variety": "Roma", "planting_date": "2026-08-15"},
            {"id": 30, "user_id": self.farmer2_id, "farm_id": 2, "crop_name": "Cotton", "variety": "Bt-2", "planting_date": "2026-06-20"}
        ]

    def _get_mock_conn(self):
        return MockFinancialConnection(self.expenses, self.harvests, self.crops, self.farms)

    # -------------------------------------------------------------------------
    # 1. AUTHENTICATION & ACCESS CONTROL
    # -------------------------------------------------------------------------
    def test_unauthorized_access(self):
        """Endpoints reject unauthorized requests with 401."""
        res_exp = self.client.get("/api/finance/expenses")
        self.assertEqual(res_exp.status_code, 401)

        res_harv = self.client.get("/api/finance/harvests")
        self.assertEqual(res_harv.status_code, 401)

        res_sum = self.client.get("/api/finance/summary")
        self.assertEqual(res_sum.status_code, 401)

    @patch("routes.financial_routes.get_db_connection")
    def test_context_crops_dropdown(self, mock_db):
        """Context crops endpoint returns authenticated farmer's registered crops and farms."""
        mock_db.return_value = self._get_mock_conn()
        res = self.client.get(
            "/api/finance/context-crops",
            headers={"Authorization": f"Bearer {self.farmer1_token}"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(len(data["crops"]), 2)
        self.assertEqual(data["crops"][0]["crop_name"], "Wheat")
        self.assertEqual(len(data["farms"]), 1)
        self.assertIn("Seeds", data["categories"])
        self.assertIn("Fertilizers", data["categories"])

    # -------------------------------------------------------------------------
    # 2. EXPENSE CRUD & VALIDATIONS
    # -------------------------------------------------------------------------
    @patch("routes.financial_routes.get_db_connection")
    def test_create_expense_success(self, mock_db):
        """Create a valid expense record."""
        mock_db.return_value = self._get_mock_conn()
        payload = {
            "farm_id": 1,
            "crop_id": 10,
            "category": "Seeds",
            "amount": 2500.50,
            "expense_date": "2026-11-05",
            "quantity": 25.0,
            "unit": "kg",
            "description": "Certified Sharbati wheat seeds",
            "notes": "Bought from local agro agency"
        }
        res = self.client.post(
            "/api/finance/expenses",
            headers={"Authorization": f"Bearer {self.farmer1_token}"},
            json=payload
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["expense"]["amount"], 2500.50)
        self.assertEqual(data["expense"]["category"], "Seeds")
        self.assertEqual(data["expense"]["crop_name"], "Wheat")
        self.assertEqual(len(self.expenses), 1)

    @patch("routes.financial_routes.get_db_connection")
    def test_create_expense_validation_errors(self, mock_db):
        """Reject invalid expense amount, invalid category, or negative quantity."""
        mock_db.return_value = self._get_mock_conn()

        # Negative amount
        res1 = self.client.post(
            "/api/finance/expenses",
            headers={"Authorization": f"Bearer {self.farmer1_token}"},
            json={"category": "Seeds", "amount": -100, "expense_date": "2026-11-01"}
        )
        self.assertEqual(res1.status_code, 400)

        # Zero amount
        res2 = self.client.post(
            "/api/finance/expenses",
            headers={"Authorization": f"Bearer {self.farmer1_token}"},
            json={"category": "Seeds", "amount": 0, "expense_date": "2026-11-01"}
        )
        self.assertEqual(res2.status_code, 400)

        # Invalid date
        res3 = self.client.post(
            "/api/finance/expenses",
            headers={"Authorization": f"Bearer {self.farmer1_token}"},
            json={"category": "Seeds", "amount": 500, "expense_date": "invalid-date"}
        )
        self.assertEqual(res3.status_code, 400)

    @patch("routes.financial_routes.get_db_connection")
    def test_expense_cross_farmer_forbidden(self, mock_db):
        """Farmer 1 cannot associate expense with Farmer 2's crop."""
        mock_db.return_value = self._get_mock_conn()
        payload = {
            "crop_id": 30,  # Belongs to Farmer 2
            "category": "Fertilizers",
            "amount": 1200.0,
            "expense_date": "2026-11-02"
        }
        res = self.client.post(
            "/api/finance/expenses",
            headers={"Authorization": f"Bearer {self.farmer1_token}"},
            json=payload
        )
        self.assertEqual(res.status_code, 403)

    @patch("routes.financial_routes.get_db_connection")
    def test_update_and_delete_expense(self, mock_db):
        """Update and delete existing expense."""
        mock_db.return_value = self._get_mock_conn()
        self.expenses.append({
            "id": 1, "user_id": self.farmer1_id, "farm_id": 1, "crop_id": 10,
            "crop_name": "Wheat", "category": "Labour", "amount": 3000.0,
            "expense_date": "2026-11-03", "quantity": 3.0, "unit": "days",
            "description": "Sowing labour", "notes": ""
        })

        # Update
        res_put = self.client.put(
            "/api/finance/expenses/1",
            headers={"Authorization": f"Bearer {self.farmer1_token}"},
            json={"category": "Labour", "amount": 3500.0, "expense_date": "2026-11-03"}
        )
        self.assertEqual(res_put.status_code, 200)
        self.assertEqual(self.expenses[0]["amount"], 3500.0)

        # Delete
        res_del = self.client.delete(
            "/api/finance/expenses/1",
            headers={"Authorization": f"Bearer {self.farmer1_token}"}
        )
        self.assertEqual(res_del.status_code, 200)
        self.assertEqual(len(self.expenses), 0)

    # -------------------------------------------------------------------------
    # 3. HARVEST & SALES CRUD & REVENUE CALCULATION
    # -------------------------------------------------------------------------
    @patch("routes.financial_routes.get_db_connection")
    def test_create_harvest_with_auto_revenue(self, mock_db):
        """Create harvest calculates total_revenue = quantity * price_per_unit."""
        mock_db.return_value = self._get_mock_conn()
        payload = {
            "farm_id": 1,
            "crop_id": 10,
            "crop_name": "Wheat",
            "harvest_date": "2026-11-08",
            "quantity": 40.0,
            "unit": "quintals",
            "price_per_unit": 2250.0,
            "buyer_name": "APMC Mandi Pune",
            "notes": "Grade A harvest"
        }
        res = self.client.post(
            "/api/finance/harvests",
            headers={"Authorization": f"Bearer {self.farmer1_token}"},
            json=payload
        )
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["harvest"]["total_revenue"], 90000.0)  # 40 * 2250
        self.assertEqual(len(self.harvests), 1)

    @patch("routes.financial_routes.get_db_connection")
    def test_harvest_validation_errors(self, mock_db):
        """Reject invalid harvest parameters."""
        mock_db.return_value = self._get_mock_conn()

        # Negative quantity
        res1 = self.client.post(
            "/api/finance/harvests",
            headers={"Authorization": f"Bearer {self.farmer1_token}"},
            json={"crop_name": "Wheat", "quantity": -5, "unit": "kg", "price_per_unit": 50, "harvest_date": "2026-11-01"}
        )
        self.assertEqual(res1.status_code, 400)

        # Missing unit
        res2 = self.client.post(
            "/api/finance/harvests",
            headers={"Authorization": f"Bearer {self.farmer1_token}"},
            json={"crop_name": "Wheat", "quantity": 10, "unit": "", "price_per_unit": 50, "harvest_date": "2026-11-01"}
        )
        self.assertEqual(res2.status_code, 400)

    # -------------------------------------------------------------------------
    # 4. SMART FINANCIAL CALCULATIONS (SUMMARY)
    # -------------------------------------------------------------------------
    @patch("routes.financial_routes.get_db_connection")
    def test_financial_summary_empty_state(self, mock_db):
        """Empty records return clear zero metrics and empty_state = True."""
        mock_db.return_value = self._get_mock_conn()
        res = self.client.get(
            "/api/finance/summary",
            headers={"Authorization": f"Bearer {self.farmer1_token}"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        s = data["summary"]
        self.assertEqual(s["total_expenses"], 0.0)
        self.assertEqual(s["total_revenue"], 0.0)
        self.assertEqual(s["net_profit"], 0.0)
        self.assertEqual(s["profit_margin"], 0.0)
        self.assertTrue(s["empty_state"])

    @patch("routes.financial_routes.get_db_connection")
    def test_financial_summary_accurate_calculations(self, mock_db):
        """Accurate calculation of net profit, profit margin, crop breakdown, and seasons."""
        mock_db.return_value = self._get_mock_conn()

        # Seed Expenses for Farmer 1: Total = 2500 + 4500 = 7000
        self.expenses.append({
            "id": 1, "user_id": self.farmer1_id, "crop_name": "Wheat",
            "category": "Seeds", "amount": 2500.0, "expense_date": "2026-11-01"
        })
        self.expenses.append({
            "id": 2, "user_id": self.farmer1_id, "crop_name": "Tomato",
            "category": "Fertilizers", "amount": 4500.0, "expense_date": "2026-09-15"
        })

        # Seed Harvest for Farmer 1: Total Revenue = 15000 + 25000 = 40000
        self.harvests.append({
            "id": 1, "user_id": self.farmer1_id, "crop_name": "Tomato",
            "quantity": 1000.0, "price_per_unit": 15.0, "total_revenue": 15000.0,
            "harvest_date": "2026-10-10"
        })
        self.harvests.append({
            "id": 2, "user_id": self.farmer1_id, "crop_name": "Wheat",
            "quantity": 10.0, "price_per_unit": 2500.0, "total_revenue": 25000.0,
            "harvest_date": "2026-11-09"
        })

        res = self.client.get(
            "/api/finance/summary",
            headers={"Authorization": f"Bearer {self.farmer1_token}"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        s = data["summary"]

        # Net Profit = 40000 - 7000 = 33000
        self.assertEqual(s["total_expenses"], 7000.0)
        self.assertEqual(s["total_revenue"], 40000.0)
        self.assertEqual(s["net_profit"], 33000.0)
        # Margin = (33000 / 40000) * 100 = 82.5%
        self.assertEqual(s["profit_margin"], 82.5)
        self.assertTrue(s["is_profitable"])
        self.assertFalse(s["empty_state"])

        # Category breakdown
        cat_map = {c["category"]: c["total_amount"] for c in data["category_breakdown"]}
        self.assertEqual(cat_map.get("Seeds"), 2500.0)
        self.assertEqual(cat_map.get("Fertilizers"), 4500.0)

        # Crop profitability
        crop_p = {c["crop_name"]: c for c in data["crop_profitability"]}
        self.assertIn("Wheat", crop_p)
        self.assertEqual(crop_p["Wheat"]["net_profit"], 22500.0)  # 25000 - 2500
        self.assertIn("Tomato", crop_p)
        self.assertEqual(crop_p["Tomato"]["net_profit"], 10500.0)  # 15000 - 4500

    # -------------------------------------------------------------------------
    # 5. STRICT FARMER DATA ISOLATION
    # -------------------------------------------------------------------------
    @patch("routes.financial_routes.get_db_connection")
    def test_farmer_data_isolation(self, mock_db):
        """Farmer 1 cannot access, edit, or delete Farmer 2's financial records."""
        mock_db.return_value = self._get_mock_conn()

        # Expense belonging to Farmer 2
        self.expenses.append({
            "id": 99, "user_id": self.farmer2_id, "crop_name": "Cotton",
            "category": "Machinery and equipment", "amount": 8000.0,
            "expense_date": "2026-11-01"
        })

        # Harvest belonging to Farmer 2
        self.harvests.append({
            "id": 88, "user_id": self.farmer2_id, "crop_name": "Cotton",
            "quantity": 50.0, "price_per_unit": 6000.0, "total_revenue": 300000.0,
            "harvest_date": "2026-11-02"
        })

        # Farmer 1 queries expense 99 -> 404
        res_get_exp = self.client.get(
            "/api/finance/expenses/99",
            headers={"Authorization": f"Bearer {self.farmer1_token}"}
        )
        self.assertEqual(res_get_exp.status_code, 404)

        # Farmer 1 queries harvest 88 -> 404
        res_get_harv = self.client.get(
            "/api/finance/harvests/88",
            headers={"Authorization": f"Bearer {self.farmer1_token}"}
        )
        self.assertEqual(res_get_harv.status_code, 404)

        # Farmer 1 summary must NOT include Farmer 2's records
        res_sum = self.client.get(
            "/api/finance/summary",
            headers={"Authorization": f"Bearer {self.farmer1_token}"}
        )
        s = res_sum.get_json()["summary"]
        self.assertEqual(s["total_expenses"], 0.0)
        self.assertEqual(s["total_revenue"], 0.0)


if __name__ == "__main__":
    unittest.main()
