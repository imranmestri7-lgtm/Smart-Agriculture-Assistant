"""AgriSmart - Smart Farm Reports Dashboard Backend Routes (Feature Upgrade 8 - Phase 1)

Provides secure, parameterized analytics and reporting endpoints covering:
- Farm Overview
- Crop Management
- Disease Diagnosis History
- Irrigation & Water Usage
- Farm Expenses, Harvest & Profit
- Farm Activities & Task Completion
- Inventory & Stock Audit
- Alerts & Notifications Summary
"""

import calendar
from datetime import date, datetime, timedelta
from flask import Blueprint, jsonify, request

from config import get_db_connection
from utils.auth_tokens import get_user_id_from_token

reports_bp = Blueprint("reports_bp", __name__, url_prefix="/api/reports")


# =============================================================================
# AUTHENTICATION & HELPER FUNCTIONS
# =============================================================================

def _authenticate():
    """Extract and validate farmer user ID from Bearer JWT token."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, (jsonify({
            "status": "error",
            "message": "Authentication required. Please log in."
        }), 401)

    token = auth_header[len("Bearer "):].strip()
    user_id = get_user_id_from_token(token)
    if user_id is None:
        return None, (jsonify({
            "status": "error",
            "message": "Invalid or expired session. Please log in again."
        }), 401)

    return user_id, None


def _format_date(val):
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d")
    return str(val)[:10]


def _format_time(val):
    if val is None:
        return None
    if isinstance(val, timedelta):
        total_seconds = int(val.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"
    if isinstance(val, datetime):
        return val.strftime("%H:%M")
    return str(val)[:5]


def _parse_disease_label(predicted_class):
    """Extract crop name, condition, and healthy status from ML model label."""
    if not predicted_class:
        return "General Plant", "Unspecified Condition", False

    clean_cls = str(predicted_class).strip()
    if "___" in clean_cls:
        crop_part, disease_part = clean_cls.split("___", 1)
        crop_name = crop_part.replace("_", " ").title()
        disease_name = disease_part.replace("_", " ").title()
        is_healthy = "healthy" in disease_part.lower()
        return crop_name, disease_name, is_healthy

    is_healthy = "healthy" in clean_cls.lower()
    return "Plant", clean_cls.replace("_", " ").title(), is_healthy


def _resolve_date_range(preset, custom_start=None, custom_end=None):
    """
    Resolve start and end dates from user filter preset or custom range.
    Supported presets:
    - today
    - last_7_days (7days)
    - last_30_days (30days)
    - current_month
    - previous_month
    - current_season (Kharif, Rabi, Zaid)
    - custom
    - all
    """
    today = date.today()
    preset = str(preset or "last_30_days").strip().lower()

    if preset == "today":
        return today, today, "Today"

    elif preset in ("last_7_days", "7days", "7_days"):
        return today - timedelta(days=6), today, "Last 7 Days"

    elif preset in ("last_30_days", "30days", "30_days"):
        return today - timedelta(days=29), today, "Last 30 Days"

    elif preset == "current_month":
        start = today.replace(day=1)
        _, last_day = calendar.monthrange(today.year, today.month)
        end = today.replace(day=last_day)
        return start, end, today.strftime("%B %Y")

    elif preset == "previous_month":
        first_of_curr = today.replace(day=1)
        prev_month_end = first_of_curr - timedelta(days=1)
        prev_month_start = prev_month_end.replace(day=1)
        return prev_month_start, prev_month_end, prev_month_start.strftime("%B %Y")

    elif preset == "current_season":
        m = today.month
        y = today.year
        if 6 <= m <= 10:
            start = date(y, 6, 1)
            end = date(y, 10, 31)
            label = f"Kharif Season {y}"
        elif m in (11, 12):
            start = date(y, 11, 1)
            end = date(y + 1, 3, 31)
            label = f"Rabi Season {y}-{y+1}"
        elif m in (1, 2, 3):
            start = date(y - 1, 11, 1)
            end = date(y, 3, 31)
            label = f"Rabi Season {y-1}-{y}"
        else:  # 4, 5
            start = date(y, 4, 1)
            end = date(y, 5, 31)
            label = f"Zaid / Summer {y}"
        return start, end, label

    elif preset == "custom" and custom_start and custom_end:
        try:
            s = datetime.strptime(str(custom_start)[:10], "%Y-%m-%d").date()
            e = datetime.strptime(str(custom_end)[:10], "%Y-%m-%d").date()
            if s > e:
                s, e = e, s
            return s, e, f"{s.strftime('%d %b %Y')} - {e.strftime('%d %b %Y')}"
        except ValueError:
            pass

    elif preset == "all":
        return None, None, "All Recorded Time"

    # Default fallback: Last 30 Days
    return today - timedelta(days=29), today, "Last 30 Days"


def _parse_common_filters():
    """Extract and resolve date range and optional farm/crop filters from query string."""
    preset = request.args.get("range", "last_30_days").strip().lower()
    start_str = request.args.get("start_date", "").strip()
    end_str = request.args.get("end_date", "").strip()

    start_date, end_date, range_label = _resolve_date_range(preset, start_str, end_str)

    farm_id = None
    farm_param = request.args.get("farm_id", "").strip()
    if farm_param and farm_param.lower() != "all" and farm_param.isdigit():
        farm_id = int(farm_param)

    crop_id = None
    crop_param = request.args.get("crop_id", "").strip()
    if crop_param and crop_param.lower() != "all" and crop_param.isdigit():
        crop_id = int(crop_param)

    return {
        "preset": preset,
        "start_date": start_date,
        "end_date": end_date,
        "range_label": range_label,
        "start_date_str": _format_date(start_date),
        "end_date_str": _format_date(end_date),
        "farm_id": farm_id,
        "crop_id": crop_id
    }


# =============================================================================
# 0. CONTEXT FOR FILTERS (FARMS & CROPS DROPDOWNS)
# =============================================================================

@reports_bp.route("/filters-context", methods=["GET"])
def get_reports_filters_context():
    """Retrieve farmer's registered farms and crops to populate report filter controls."""
    user_id, err = _authenticate()
    if err:
        return err

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, farm_name, location FROM farms WHERE user_id = %s ORDER BY farm_name ASC", (user_id,))
        farms = cursor.fetchall() or []

        cursor.execute("""
            SELECT c.id, c.crop_name, c.variety, c.growth_status, f.farm_name
            FROM crops c
            LEFT JOIN farms f ON c.farm_id = f.id
            WHERE c.user_id = %s
            ORDER BY c.crop_name ASC
        """, (user_id,))
        crops = cursor.fetchall() or []

        return jsonify({
            "status": "success",
            "farms": [{"id": f["id"], "farm_name": f["farm_name"], "location": f.get("location") or ""} for f in farms],
            "crops": [{"id": c["id"], "crop_name": c["crop_name"], "variety": c.get("variety") or "", "farm_name": c.get("farm_name") or ""} for c in crops]
        }), 200

    except Exception as e:
        print(f"Error fetching report filters context: {e}")
        return jsonify({"status": "error", "message": "Failed to load report filter context."}), 500
    finally:
        if conn:
            conn.close()


# =============================================================================
# 1. FARM OVERVIEW REPORT
# =============================================================================

@reports_bp.route("/overview", methods=["GET"])
def get_farm_overview_report():
    """
    Consolidated Farm Overview Report aggregating metrics across all 8 modules:
    farms, crops, activities, finances, inventory, disease diagnoses, irrigation & alerts.
    """
    user_id, err = _authenticate()
    if err:
        return err

    flt = _parse_common_filters()
    start_d = flt["start_date"]
    end_d = flt["end_date"]
    farm_id = flt["farm_id"]
    crop_id = flt["crop_id"]

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        today = date.today()

        # 1. Farms Metric
        farm_query = "SELECT COUNT(*) AS total_farms, COALESCE(SUM(total_area), 0.0) AS total_area FROM farms WHERE user_id = %s"
        farm_params = [user_id]
        if farm_id:
            farm_query += " AND id = %s"
            farm_params.append(farm_id)
        cursor.execute(farm_query, tuple(farm_params))
        farm_row = cursor.fetchone() or {}
        total_farms = int(farm_row.get("total_farms") or 0)
        total_farm_area = float(farm_row.get("total_area") or 0.0)

        # 2. Crops Metric
        crop_query = """
            SELECT 
                COUNT(*) AS total_crops,
                SUM(CASE WHEN growth_status != 'Harvested' THEN 1 ELSE 0 END) AS active_crops,
                SUM(CASE WHEN growth_status = 'Harvested' THEN 1 ELSE 0 END) AS harvested_crops,
                COALESCE(SUM(cultivated_area), 0.0) AS total_cultivated_area
            FROM crops
            WHERE user_id = %s
        """
        crop_params = [user_id]
        if farm_id:
            crop_query += " AND farm_id = %s"
            crop_params.append(farm_id)
        if crop_id:
            crop_query += " AND id = %s"
            crop_params.append(crop_id)
        cursor.execute(crop_query, tuple(crop_params))
        crop_row = cursor.fetchone() or {}
        total_crops = int(crop_row.get("total_crops") or 0)
        active_crops = int(crop_row.get("active_crops") or 0)
        harvested_crops = int(crop_row.get("harvested_crops") or 0)
        total_cultivated_area = float(crop_row.get("total_cultivated_area") or 0.0)

        # 3. Activities Metric (filtered by date range)
        act_query = """
            SELECT 
                COUNT(*) AS total_activities,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed_activities,
                SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) AS pending_activities,
                SUM(CASE WHEN status = 'In-Progress' OR status = 'InProgress' THEN 1 ELSE 0 END) AS in_progress_activities,
                SUM(CASE WHEN status = 'Pending' AND scheduled_date < %s THEN 1 ELSE 0 END) AS overdue_activities
            FROM farm_activities
            WHERE user_id = %s
        """
        act_params = [today, user_id]
        if start_d and end_d:
            act_query += " AND scheduled_date >= %s AND scheduled_date <= %s"
            act_params.extend([start_d, end_d])
        if farm_id:
            act_query += " AND farm_id = %s"
            act_params.append(farm_id)
        if crop_id:
            act_query += " AND crop_id = %s"
            act_params.append(crop_id)

        cursor.execute(act_query, tuple(act_params))
        act_row = cursor.fetchone() or {}
        total_activities = int(act_row.get("total_activities") or 0)
        completed_activities = int(act_row.get("completed_activities") or 0)
        pending_activities = int(act_row.get("pending_activities") or 0)
        in_progress_activities = int(act_row.get("in_progress_activities") or 0)
        overdue_activities = int(act_row.get("overdue_activities") or 0)
        completion_rate = round((completed_activities / total_activities * 100), 1) if total_activities > 0 else 0.0

        # 4. Financials (Expenses & Harvest Revenue in date range)
        exp_query = "SELECT COALESCE(SUM(amount), 0.0) AS total_expenses, COUNT(*) AS count_expenses FROM farm_expenses WHERE user_id = %s"
        exp_params = [user_id]
        if start_d and end_d:
            exp_query += " AND expense_date >= %s AND expense_date <= %s"
            exp_params.extend([start_d, end_d])
        if farm_id:
            exp_query += " AND farm_id = %s"
            exp_params.append(farm_id)
        if crop_id:
            exp_query += " AND crop_id = %s"
            exp_params.append(crop_id)
        cursor.execute(exp_query, tuple(exp_params))
        exp_row = cursor.fetchone() or {}
        total_expenses = float(exp_row.get("total_expenses") or 0.0)

        rev_query = "SELECT COALESCE(SUM(total_revenue), 0.0) AS total_revenue, COUNT(*) AS count_harvests FROM farm_harvests WHERE user_id = %s"
        rev_params = [user_id]
        if start_d and end_d:
            rev_query += " AND harvest_date >= %s AND harvest_date <= %s"
            rev_params.extend([start_d, end_d])
        if farm_id:
            rev_query += " AND farm_id = %s"
            rev_params.append(farm_id)
        if crop_id:
            rev_query += " AND crop_id = %s"
            rev_params.append(crop_id)
        cursor.execute(rev_query, tuple(rev_params))
        rev_row = cursor.fetchone() or {}
        total_revenue = float(rev_row.get("total_revenue") or 0.0)

        net_profit = round(total_revenue - total_expenses, 2)
        profit_margin = round((net_profit / total_revenue * 100), 1) if total_revenue > 0 else 0.0

        # 5. Inventory Metrics
        inv_query = """
            SELECT 
                COUNT(*) AS total_items,
                COALESCE(SUM(quantity * purchase_price), 0.0) AS total_valuation,
                SUM(CASE WHEN quantity > 0 AND quantity <= min_threshold THEN 1 ELSE 0 END) AS low_stock_count,
                SUM(CASE WHEN quantity <= 0 THEN 1 ELSE 0 END) AS out_of_stock_count,
                SUM(CASE WHEN expiry_date IS NOT NULL AND expiry_date >= %s AND expiry_date <= %s THEN 1 ELSE 0 END) AS expiring_count,
                SUM(CASE WHEN expiry_date IS NOT NULL AND expiry_date < %s THEN 1 ELSE 0 END) AS expired_count
            FROM farm_inventory
            WHERE user_id = %s
        """
        expiring_threshold = today + timedelta(days=30)
        inv_params = [today, expiring_threshold, today, user_id]
        if farm_id:
            inv_query += " AND farm_id = %s"
            inv_params.append(farm_id)
        cursor.execute(inv_query, tuple(inv_params))
        inv_row = cursor.fetchone() or {}
        total_inventory_items = int(inv_row.get("total_items") or 0)
        total_inventory_valuation = float(inv_row.get("total_valuation") or 0.0)
        low_stock_count = int(inv_row.get("low_stock_count") or 0)
        out_of_stock_count = int(inv_row.get("out_of_stock_count") or 0)
        expiring_count = int(inv_row.get("expiring_count") or 0)
        expired_count = int(inv_row.get("expired_count") or 0)

        # 6. Disease Diagnoses Metric (filtered by date range)
        diag_query = "SELECT COUNT(*) AS total_scans, AVG(confidence) AS avg_conf FROM diagnosis_history WHERE user_id = %s"
        diag_params = [user_id]
        if start_d and end_d:
            diag_query += " AND diagnosis_date >= %s AND diagnosis_date <= %s"
            diag_params.extend([start_d, end_d])
        if crop_id:
            diag_query += " AND crop_id = %s"
            diag_params.append(crop_id)
        cursor.execute(diag_query, tuple(diag_params))
        diag_row = cursor.fetchone() or {}
        total_scans = int(diag_row.get("total_scans") or 0)
        avg_confidence = round(float(diag_row.get("avg_conf") or 0.0) * 100, 1)

        # 7. Irrigation Checks Metric (filtered by date range)
        irrig_query = """
            SELECT 
                COUNT(*) AS total_checks,
                COALESCE(SUM(water_quantity_mm), 0.0) AS total_water_applied_mm,
                COALESCE(SUM(water_saved_mm), 0.0) AS total_water_saved_mm,
                SUM(CASE WHEN is_irrigation_needed = 1 THEN 1 ELSE 0 END) AS irrigation_needed_count,
                AVG(soil_moisture) AS avg_soil_moisture
            FROM irrigation_history
            WHERE user_id = %s
        """
        irrig_params = [user_id]
        if start_d and end_d:
            irrig_query += " AND DATE(created_at) >= %s AND DATE(created_at) <= %s"
            irrig_params.extend([start_d, end_d])
        cursor.execute(irrig_query, tuple(irrig_params))
        irrig_row = cursor.fetchone() or {}
        total_irrigation_checks = int(irrig_row.get("total_checks") or 0)
        total_water_applied_mm = round(float(irrig_row.get("total_water_applied_mm") or 0.0), 1)
        total_water_saved_mm = round(float(irrig_row.get("total_water_saved_mm") or 0.0), 1)
        irrigation_needed_count = int(irrig_row.get("irrigation_needed_count") or 0)
        avg_soil_moisture = round(float(irrig_row.get("avg_soil_moisture") or 0.0), 1)

        # 8. Notifications / Alerts Metric
        notif_query = """
            SELECT 
                COUNT(*) AS total_alerts,
                SUM(CASE WHEN is_read = 0 THEN 1 ELSE 0 END) AS unread_alerts,
                SUM(CASE WHEN severity = 'urgent' THEN 1 ELSE 0 END) AS urgent_alerts
            FROM notifications
            WHERE user_id = %s
        """
        notif_params = [user_id]
        if start_d and end_d:
            notif_query += " AND DATE(created_at) >= %s AND DATE(created_at) <= %s"
            notif_params.extend([start_d, end_d])
        cursor.execute(notif_query, tuple(notif_params))
        notif_row = cursor.fetchone() or {}
        total_alerts = int(notif_row.get("total_alerts") or 0)
        unread_alerts = int(notif_row.get("unread_alerts") or 0)
        urgent_alerts = int(notif_row.get("urgent_alerts") or 0)

        # 9. Recent Activity Highlights
        cursor.execute("""
            SELECT a.title, a.category, a.scheduled_date, a.status, c.crop_name, f.farm_name
            FROM farm_activities a
            LEFT JOIN crops c ON a.crop_id = c.id
            LEFT JOIN farms f ON a.farm_id = f.id
            WHERE a.user_id = %s
            ORDER BY a.scheduled_date DESC, a.id DESC
            LIMIT 5
        """, (user_id,))
        recent_activities = []
        for r in cursor.fetchall():
            recent_activities.append({
                "title": r["title"],
                "category": r["category"],
                "date": _format_date(r["scheduled_date"]),
                "status": r["status"],
                "crop_name": r.get("crop_name"),
                "farm_name": r.get("farm_name")
            })

        report_data = {
            "filters": {
                "preset": flt["preset"],
                "range_label": flt["range_label"],
                "start_date": flt["start_date_str"],
                "end_date": flt["end_date_str"],
                "farm_id": farm_id,
                "crop_id": crop_id
            },
            "farms": {
                "total_farms": total_farms,
                "total_area": total_farm_area
            },
            "crops": {
                "total_crops": total_crops,
                "active_crops": active_crops,
                "harvested_crops": harvested_crops,
                "total_cultivated_area": total_cultivated_area
            },
            "activities": {
                "total_activities": total_activities,
                "completed": completed_activities,
                "pending": pending_activities,
                "in_progress": in_progress_activities,
                "overdue": overdue_activities,
                "completion_rate": completion_rate
            },
            "financials": {
                "total_expenses": total_expenses,
                "total_revenue": total_revenue,
                "net_profit": net_profit,
                "profit_margin": profit_margin
            },
            "inventory": {
                "total_items": total_inventory_items,
                "total_valuation": total_inventory_valuation,
                "low_stock_count": low_stock_count,
                "out_of_stock_count": out_of_stock_count,
                "expiring_soon_count": expiring_count,
                "expired_count": expired_count
            },
            "disease": {
                "total_scans": total_scans,
                "avg_confidence": avg_confidence
            },
            "irrigation": {
                "total_checks": total_irrigation_checks,
                "water_applied_mm": total_water_applied_mm,
                "water_saved_mm": total_water_saved_mm,
                "irrigation_needed_count": irrigation_needed_count,
                "avg_soil_moisture": avg_soil_moisture
            },
            "alerts": {
                "total_alerts": total_alerts,
                "unread_alerts": unread_alerts,
                "urgent_alerts": urgent_alerts
            },
            "recent_activities": recent_activities
        }

        return jsonify({
            "status": "success",
            "report_type": "overview",
            "data": report_data
        }), 200

    except Exception as e:
        print(f"Error generating overview report: {e}")
        return jsonify({"status": "error", "message": "Failed to generate farm overview report."}), 500
    finally:
        if conn:
            conn.close()


# =============================================================================
# 2. CROP MANAGEMENT REPORT
# =============================================================================

@reports_bp.route("/crops", methods=["GET"])
def get_crop_management_report():
    """Detailed Crop Management Report: varieties, stages, growth statuses & crops table."""
    user_id, err = _authenticate()
    if err:
        return err

    flt = _parse_common_filters()
    farm_id = flt["farm_id"]
    crop_id = flt["crop_id"]
    start_d = flt["start_date"]
    end_d = flt["end_date"]

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT c.*, f.farm_name, f.location AS farm_location
            FROM crops c
            LEFT JOIN farms f ON c.farm_id = f.id
            WHERE c.user_id = %s
        """
        params = [user_id]
        if farm_id:
            query += " AND c.farm_id = %s"
            params.append(farm_id)
        if crop_id:
            query += " AND c.id = %s"
            params.append(crop_id)
        if start_d and end_d:
            query += " AND c.planting_date >= %s AND c.planting_date <= %s"
            params.extend([start_d, end_d])

        query += " ORDER BY c.growth_status ASC, c.crop_name ASC"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall() or []

        total_crops = len(rows)
        active_crops = sum(1 for r in rows if r.get("growth_status") != "Harvested")
        harvested_crops = total_crops - active_crops
        total_area = sum(float(r.get("cultivated_area") or 0.0) for r in rows)

        status_counts = {}
        variety_counts = {}
        crops_list = []
        today = date.today()

        for r in rows:
            st = r.get("growth_status") or "Newly Planted"
            status_counts[st] = status_counts.get(st, 0) + 1

            cname = r.get("crop_name") or "General"
            variety_counts[cname] = variety_counts.get(cname, 0) + 1

            pdate = r.get("planting_date")
            days_planted = 0
            if pdate:
                p_obj = pdate if isinstance(pdate, date) else datetime.strptime(str(pdate)[:10], "%Y-%m-%d").date()
                days_planted = max(0, (today - p_obj).days)

            crops_list.append({
                "id": r["id"],
                "crop_name": r["crop_name"],
                "variety": r.get("variety") or "",
                "farm_name": r.get("farm_name") or "General Farm",
                "farm_location": r.get("farm_location") or "",
                "planting_date": _format_date(r.get("planting_date")),
                "expected_harvest_date": _format_date(r.get("expected_harvest_date")),
                "cultivated_area": float(r.get("cultivated_area") or 0.0),
                "area_unit": r.get("area_unit") or "acres",
                "growth_status": st,
                "days_in_ground": days_planted,
                "notes": r.get("notes") or ""
            })

        return jsonify({
            "status": "success",
            "report_type": "crops",
            "filters": {
                "preset": flt["preset"],
                "range_label": flt["range_label"],
                "start_date": flt["start_date_str"],
                "end_date": flt["end_date_str"]
            },
            "data": {
                "total_crops": total_crops,
                "active_crops": active_crops,
                "harvested_crops": harvested_crops,
                "total_area": round(total_area, 2),
                "status_distribution": status_counts,
                "variety_distribution": variety_counts,
                "crops_list": crops_list
            }
        }), 200

    except Exception as e:
        print(f"Error generating crops report: {e}")
        return jsonify({"status": "error", "message": "Failed to generate crops report."}), 500
    finally:
        if conn:
            conn.close()


# =============================================================================
# 3. DISEASE DIAGNOSIS REPORT
# =============================================================================

@reports_bp.route("/disease", methods=["GET"])
def get_disease_diagnosis_report():
    """Disease Diagnosis Report: scan totals, healthy rate, top conditions & scan logs."""
    user_id, err = _authenticate()
    if err:
        return err

    flt = _parse_common_filters()
    start_d = flt["start_date"]
    end_d = flt["end_date"]
    crop_id = flt["crop_id"]

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT d.*, c.crop_name AS assigned_crop_name
            FROM diagnosis_history d
            LEFT JOIN crops c ON d.crop_id = c.id
            WHERE d.user_id = %s
        """
        params = [user_id]
        if start_d and end_d:
            query += " AND d.diagnosis_date >= %s AND d.diagnosis_date <= %s"
            params.extend([start_d, end_d])
        if crop_id:
            query += " AND d.crop_id = %s"
            params.append(crop_id)

        query += " ORDER BY d.diagnosis_date DESC, d.id DESC"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall() or []

        total_scans = len(rows)
        healthy_scans = 0
        diseased_scans = 0
        conf_sum = 0.0
        disease_counts = {}
        scans_list = []

        for r in rows:
            cls = r.get("predicted_class") or ""
            crop_name_parsed, disease_name_parsed, is_healthy = _parse_disease_label(cls)
            crop_name = r.get("assigned_crop_name") or crop_name_parsed

            conf = float(r.get("confidence") or 0.0)
            conf_sum += conf

            if is_healthy:
                healthy_scans += 1
                disease_counts["Healthy Foliage"] = disease_counts.get("Healthy Foliage", 0) + 1
            else:
                diseased_scans += 1
                disease_counts[disease_name_parsed] = disease_counts.get(disease_name_parsed, 0) + 1

            scans_list.append({
                "id": r["id"],
                "crop_name": crop_name,
                "disease_name": disease_name_parsed,
                "predicted_class": cls,
                "confidence": round(conf * 100, 1),
                "is_healthy": is_healthy,
                "diagnosis_date": _format_date(r.get("diagnosis_date")),
                "image_path": r.get("image_path") or "",
                "notes": r.get("notes") or ""
            })

        avg_conf = round((conf_sum / total_scans * 100), 1) if total_scans > 0 else 0.0
        healthy_rate = round((healthy_scans / total_scans * 100), 1) if total_scans > 0 else 0.0

        return jsonify({
            "status": "success",
            "report_type": "disease",
            "filters": {
                "preset": flt["preset"],
                "range_label": flt["range_label"],
                "start_date": flt["start_date_str"],
                "end_date": flt["end_date_str"]
            },
            "data": {
                "total_scans": total_scans,
                "healthy_scans": healthy_scans,
                "diseased_scans": diseased_scans,
                "healthy_rate_pct": healthy_rate,
                "avg_confidence_pct": avg_conf,
                "disease_distribution": disease_counts,
                "scans_list": scans_list
            }
        }), 200

    except Exception as e:
        print(f"Error generating disease report: {e}")
        return jsonify({"status": "error", "message": "Failed to generate disease report."}), 500
    finally:
        if conn:
            conn.close()


# =============================================================================
# 4. IRRIGATION & WATER USAGE REPORT
# =============================================================================

@reports_bp.route("/irrigation", methods=["GET"])
def get_irrigation_report():
    """Irrigation & Water Usage Report: volume applied, water saved, recommendations & history."""
    user_id, err = _authenticate()
    if err:
        return err

    flt = _parse_common_filters()
    start_d = flt["start_date"]
    end_d = flt["end_date"]

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = "SELECT * FROM irrigation_history WHERE user_id = %s"
        params = [user_id]
        if start_d and end_d:
            query += " AND DATE(created_at) >= %s AND DATE(created_at) <= %s"
            params.extend([start_d, end_d])

        query += " ORDER BY created_at DESC, id DESC"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall() or []

        total_records = len(rows)
        total_water_mm = sum(float(r.get("water_quantity_mm") or 0.0) for r in rows)
        total_water_saved_mm = sum(float(r.get("water_saved_mm") or 0.0) for r in rows)
        needed_count = sum(1 for r in rows if r.get("is_irrigation_needed") == 1)
        not_needed_count = total_records - needed_count

        moisture_vals = [float(r["soil_moisture"]) for r in rows if r.get("soil_moisture") is not None]
        avg_moisture = round(sum(moisture_vals) / len(moisture_vals), 1) if moisture_vals else 0.0

        crop_water_usage = {}
        recommendation_counts = {}
        records_list = []

        for r in rows:
            crop = r.get("crop") or "General"
            w_mm = float(r.get("water_quantity_mm") or 0.0)
            crop_water_usage[crop] = crop_water_usage.get(crop, 0.0) + w_mm

            st = r.get("recommendation_status") or ("Irrigation Needed" if r.get("is_irrigation_needed") else "Sufficient Moisture")
            recommendation_counts[st] = recommendation_counts.get(st, 0) + 1

            records_list.append({
                "id": r["id"],
                "crop": crop,
                "soil_moisture": float(r["soil_moisture"]) if r.get("soil_moisture") is not None else None,
                "temperature": float(r["temperature"]) if r.get("temperature") is not None else None,
                "humidity": float(r["humidity"]) if r.get("humidity") is not None else None,
                "rainfall": float(r["rainfall"]) if r.get("rainfall") is not None else None,
                "location": r.get("location") or "",
                "soil_type": r.get("soil_type") or "",
                "growth_stage": r.get("growth_stage") or "",
                "is_irrigation_needed": bool(r.get("is_irrigation_needed")),
                "recommendation_status": st,
                "water_quantity_mm": w_mm,
                "water_saved_mm": float(r.get("water_saved_mm") or 0.0),
                "created_at": _format_date(r.get("created_at"))
            })

        # Round crop totals
        for c in crop_water_usage:
            crop_water_usage[c] = round(crop_water_usage[c], 1)

        return jsonify({
            "status": "success",
            "report_type": "irrigation",
            "filters": {
                "preset": flt["preset"],
                "range_label": flt["range_label"],
                "start_date": flt["start_date_str"],
                "end_date": flt["end_date_str"]
            },
            "data": {
                "total_records": total_records,
                "total_water_applied_mm": round(total_water_mm, 1),
                "total_water_saved_mm": round(total_water_saved_mm, 1),
                "irrigation_needed_count": needed_count,
                "not_needed_count": not_needed_count,
                "avg_soil_moisture": avg_moisture,
                "crop_water_usage": crop_water_usage,
                "recommendation_distribution": recommendation_counts,
                "records_list": records_list
            }
        }), 200

    except Exception as e:
        print(f"Error generating irrigation report: {e}")
        return jsonify({"status": "error", "message": "Failed to generate irrigation report."}), 500
    finally:
        if conn:
            conn.close()


# =============================================================================
# 5. FARM EXPENSES & PROFIT REPORT
# =============================================================================

@reports_bp.route("/financial", methods=["GET"])
def get_financial_report():
    """Farm Financial Report: expense categories, harvest sales, crop profitability & ledger."""
    user_id, err = _authenticate()
    if err:
        return err

    flt = _parse_common_filters()
    start_d = flt["start_date"]
    end_d = flt["end_date"]
    farm_id = flt["farm_id"]
    crop_id = flt["crop_id"]

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Expenses
        exp_q = """
            SELECT e.*, c.crop_name AS joined_crop_name, f.farm_name
            FROM farm_expenses e
            LEFT JOIN crops c ON e.crop_id = c.id
            LEFT JOIN farms f ON e.farm_id = f.id
            WHERE e.user_id = %s
        """
        exp_p = [user_id]
        if start_d and end_d:
            exp_q += " AND e.expense_date >= %s AND e.expense_date <= %s"
            exp_p.extend([start_d, end_d])
        if farm_id:
            exp_q += " AND e.farm_id = %s"
            exp_p.append(farm_id)
        if crop_id:
            exp_q += " AND e.crop_id = %s"
            exp_p.append(crop_id)

        exp_q += " ORDER BY e.expense_date DESC, e.id DESC"
        cursor.execute(exp_q, tuple(exp_p))
        exp_rows = cursor.fetchall() or []

        # 2. Harvests / Revenue
        harv_q = """
            SELECT h.*, c.crop_name AS joined_crop_name, f.farm_name
            FROM farm_harvests h
            LEFT JOIN crops c ON h.crop_id = c.id
            LEFT JOIN farms f ON h.farm_id = f.id
            WHERE h.user_id = %s
        """
        harv_p = [user_id]
        if start_d and end_d:
            harv_q += " AND h.harvest_date >= %s AND h.harvest_date <= %s"
            harv_p.extend([start_d, end_d])
        if farm_id:
            harv_q += " AND h.farm_id = %s"
            harv_p.append(farm_id)
        if crop_id:
            harv_q += " AND h.crop_id = %s"
            harv_p.append(crop_id)

        harv_q += " ORDER BY h.harvest_date DESC, h.id DESC"
        cursor.execute(harv_q, tuple(harv_p))
        harv_rows = cursor.fetchall() or []

        total_expenses = sum(float(r["amount"]) for r in exp_rows)
        total_revenue = sum(float(r["total_revenue"]) for r in harv_rows)
        net_profit = round(total_revenue - total_expenses, 2)
        profit_margin = round((net_profit / total_revenue * 100), 1) if total_revenue > 0 else 0.0

        # Category breakdown
        category_breakdown = {}
        for r in exp_rows:
            cat = r.get("category") or "Other"
            category_breakdown[cat] = category_breakdown.get(cat, 0.0) + float(r["amount"])
        for k in category_breakdown:
            category_breakdown[k] = round(category_breakdown[k], 2)

        # Buyer breakdown
        buyer_breakdown = {}
        for r in harv_rows:
            buyer = r.get("buyer_name") or "Direct Consumer / Local APMC"
            buyer_breakdown[buyer] = buyer_breakdown.get(buyer, 0.0) + float(r["total_revenue"])
        for b in buyer_breakdown:
            buyer_breakdown[b] = round(buyer_breakdown[b], 2)

        # Crop Profitability Analysis
        crop_fin = {}
        for r in exp_rows:
            cname = r.get("joined_crop_name") or r.get("crop_name") or "General Farm Expenses"
            if cname not in crop_fin:
                crop_fin[cname] = {"expenses": 0.0, "revenue": 0.0}
            crop_fin[cname]["expenses"] += float(r["amount"])

        for r in harv_rows:
            cname = r.get("joined_crop_name") or r.get("crop_name") or "General Farm Harvests"
            if cname not in crop_fin:
                crop_fin[cname] = {"expenses": 0.0, "revenue": 0.0}
            crop_fin[cname]["revenue"] += float(r["total_revenue"])

        crop_profitability = []
        for cname, vals in crop_fin.items():
            exp_val = round(vals["expenses"], 2)
            rev_val = round(vals["revenue"], 2)
            prof_val = round(rev_val - exp_val, 2)
            crop_profitability.append({
                "crop_name": cname,
                "expenses": exp_val,
                "revenue": rev_val,
                "net_profit": prof_val,
                "margin_pct": round((prof_val / rev_val * 100), 1) if rev_val > 0 else 0.0
            })
        crop_profitability.sort(key=lambda x: x["net_profit"], reverse=True)

        # Expense records formatting
        expense_records = []
        for r in exp_rows:
            expense_records.append({
                "id": r["id"],
                "date": _format_date(r["expense_date"]),
                "category": r["category"],
                "amount": float(r["amount"]),
                "crop_name": r.get("joined_crop_name") or r.get("crop_name") or "General",
                "farm_name": r.get("farm_name") or "General Farm",
                "description": r.get("description") or "",
                "notes": r.get("notes") or ""
            })

        # Harvest records formatting
        harvest_records = []
        for r in harv_rows:
            harvest_records.append({
                "id": r["id"],
                "date": _format_date(r["harvest_date"]),
                "crop_name": r.get("joined_crop_name") or r.get("crop_name") or "Crop",
                "farm_name": r.get("farm_name") or "General Farm",
                "quantity": float(r["quantity"]),
                "unit": r.get("unit") or "kg",
                "price_per_unit": float(r.get("price_per_unit") or 0.0),
                "total_revenue": float(r["total_revenue"]),
                "buyer_name": r.get("buyer_name") or "",
                "notes": r.get("notes") or ""
            })

        return jsonify({
            "status": "success",
            "report_type": "financial",
            "filters": {
                "preset": flt["preset"],
                "range_label": flt["range_label"],
                "start_date": flt["start_date_str"],
                "end_date": flt["end_date_str"]
            },
            "data": {
                "total_expenses": round(total_expenses, 2),
                "total_revenue": round(total_revenue, 2),
                "net_profit": net_profit,
                "profit_margin_pct": profit_margin,
                "expense_categories": category_breakdown,
                "buyer_breakdown": buyer_breakdown,
                "crop_profitability": crop_profitability,
                "expense_records": expense_records,
                "harvest_records": harvest_records
            }
        }), 200

    except Exception as e:
        print(f"Error generating financial report: {e}")
        return jsonify({"status": "error", "message": "Failed to generate financial report."}), 500
    finally:
        if conn:
            conn.close()


# =============================================================================
# 6. FARM ACTIVITIES & TASKS REPORT
# =============================================================================

@reports_bp.route("/activities", methods=["GET"])
def get_activities_report():
    """Farm Activities & Task Planner Report: completion rates, categories, priorities & tasks list."""
    user_id, err = _authenticate()
    if err:
        return err

    flt = _parse_common_filters()
    start_d = flt["start_date"]
    end_d = flt["end_date"]
    farm_id = flt["farm_id"]
    crop_id = flt["crop_id"]

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        today = date.today()

        query = """
            SELECT a.*, c.crop_name, f.farm_name
            FROM farm_activities a
            LEFT JOIN crops c ON a.crop_id = c.id
            LEFT JOIN farms f ON a.farm_id = f.id
            WHERE a.user_id = %s
        """
        params = [user_id]
        if start_d and end_d:
            query += " AND a.scheduled_date >= %s AND a.scheduled_date <= %s"
            params.extend([start_d, end_d])
        if farm_id:
            query += " AND a.farm_id = %s"
            params.append(farm_id)
        if crop_id:
            query += " AND a.crop_id = %s"
            params.append(crop_id)

        query += " ORDER BY a.scheduled_date DESC, a.id DESC"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall() or []

        total_activities = len(rows)
        completed_count = 0
        pending_count = 0
        in_progress_count = 0
        postponed_count = 0
        overdue_count = 0

        category_counts = {}
        priority_counts = {}
        activities_list = []

        for r in rows:
            st = r.get("status") or "Pending"
            sdate = r.get("scheduled_date")
            is_overdue = False

            if sdate:
                s_obj = sdate if isinstance(sdate, date) else datetime.strptime(str(sdate)[:10], "%Y-%m-%d").date()
                if st == "Pending" and s_obj < today:
                    overdue_count += 1
                    is_overdue = True

            if st == "Completed":
                completed_count += 1
            elif st == "Pending":
                pending_count += 1
            elif st in ("In-Progress", "InProgress"):
                in_progress_count += 1
            elif st == "Postponed":
                postponed_count += 1

            cat = r.get("category") or "Other activities"
            category_counts[cat] = category_counts.get(cat, 0) + 1

            pri = r.get("priority") or "Medium"
            priority_counts[pri] = priority_counts.get(pri, 0) + 1

            activities_list.append({
                "id": r["id"],
                "title": r["title"],
                "category": cat,
                "priority": pri,
                "status": st,
                "is_overdue": is_overdue,
                "scheduled_date": _format_date(sdate),
                "scheduled_time": _format_time(r.get("scheduled_time")),
                "completion_date": _format_date(r.get("completion_date")),
                "crop_name": r.get("crop_name"),
                "farm_name": r.get("farm_name"),
                "description": r.get("description") or "",
                "notes": r.get("notes") or ""
            })

        completion_rate = round((completed_count / total_activities * 100), 1) if total_activities > 0 else 0.0

        return jsonify({
            "status": "success",
            "report_type": "activities",
            "filters": {
                "preset": flt["preset"],
                "range_label": flt["range_label"],
                "start_date": flt["start_date_str"],
                "end_date": flt["end_date_str"]
            },
            "data": {
                "total_activities": total_activities,
                "completed_count": completed_count,
                "pending_count": pending_count,
                "in_progress_count": in_progress_count,
                "postponed_count": postponed_count,
                "overdue_count": overdue_count,
                "completion_rate_pct": completion_rate,
                "category_distribution": category_counts,
                "priority_distribution": priority_counts,
                "activities_list": activities_list
            }
        }), 200

    except Exception as e:
        print(f"Error generating activities report: {e}")
        return jsonify({"status": "error", "message": "Failed to generate activities report."}), 500
    finally:
        if conn:
            conn.close()


# =============================================================================
# 7. INVENTORY & STOCK REPORT
# =============================================================================

@reports_bp.route("/inventory", methods=["GET"])
def get_inventory_report():
    """Inventory & Stock Audit Report: valuation, categories, stock buffer levels & items ledger."""
    user_id, err = _authenticate()
    if err:
        return err

    flt = _parse_common_filters()
    farm_id = flt["farm_id"]
    start_d = flt["start_date"]
    end_d = flt["end_date"]

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        today = date.today()

        # 1. Active Inventory Items
        query = """
            SELECT i.*, f.farm_name
            FROM farm_inventory i
            LEFT JOIN farms f ON i.farm_id = f.id
            WHERE i.user_id = %s
        """
        params = [user_id]
        if farm_id:
            query += " AND i.farm_id = %s"
            params.append(farm_id)

        query += " ORDER BY i.item_name ASC"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall() or []

        total_items = len(rows)
        total_valuation = 0.0
        low_stock_count = 0
        out_of_stock_count = 0
        expiring_count = 0
        expired_count = 0

        category_breakdown = {}
        status_breakdown = {
            "In Stock": 0,
            "Low Stock": 0,
            "Out of Stock": 0,
            "Expiring Soon": 0,
            "Expired": 0
        }
        items_list = []

        for r in rows:
            qty = float(r.get("quantity") or 0.0)
            threshold = float(r.get("min_threshold") or 0.0)
            price = float(r.get("purchase_price") or 0.0)
            val = round(qty * price, 2)
            total_valuation += val

            cat = r.get("category") or "Other agricultural supplies"
            if cat not in category_breakdown:
                category_breakdown[cat] = {"count": 0, "valuation": 0.0}
            category_breakdown[cat]["count"] += 1
            category_breakdown[cat]["valuation"] = round(category_breakdown[cat]["valuation"] + val, 2)

            exp = r.get("expiry_date")
            exp_date_obj = None
            if exp:
                exp_date_obj = exp if isinstance(exp, date) else datetime.strptime(str(exp)[:10], "%Y-%m-%d").date()

            # Determine status
            status = "In Stock"
            if qty <= 0:
                status = "Out of Stock"
                out_of_stock_count += 1
            elif exp_date_obj and exp_date_obj < today:
                status = "Expired"
                expired_count += 1
            elif qty <= threshold:
                status = "Low Stock"
                low_stock_count += 1
            elif exp_date_obj and 0 <= (exp_date_obj - today).days <= 30:
                status = "Expiring Soon"
                expiring_count += 1

            status_breakdown[status] = status_breakdown.get(status, 0) + 1

            items_list.append({
                "id": r["id"],
                "item_name": r["item_name"],
                "category": cat,
                "quantity": qty,
                "unit": r.get("unit") or "kg",
                "purchase_price": price,
                "total_value": val,
                "min_threshold": threshold,
                "expiry_date": _format_date(exp),
                "farm_name": r.get("farm_name") or "General Farm",
                "storage_location": r.get("storage_location") or "",
                "status": status
            })

        # 2. Stock Movements in date range
        mov_query = """
            SELECT m.*, i.item_name, c.crop_name, f.farm_name
            FROM farm_inventory_movements m
            JOIN farm_inventory i ON m.inventory_id = i.id
            LEFT JOIN crops c ON m.crop_id = c.id
            LEFT JOIN farms f ON m.farm_id = f.id
            WHERE m.user_id = %s
        """
        mov_params = [user_id]
        if start_d and end_d:
            mov_query += " AND m.movement_date >= %s AND m.movement_date <= %s"
            mov_params.extend([start_d, end_d])
        if farm_id:
            mov_query += " AND m.farm_id = %s"
            mov_params.append(farm_id)

        mov_query += " ORDER BY m.movement_date DESC, m.id DESC LIMIT 50"
        cursor.execute(mov_query, tuple(mov_params))
        mov_rows = cursor.fetchall() or []

        movement_types = {}
        movements_list = []
        for m in mov_rows:
            mtype = m.get("movement_type") or "Usage / Consumption"
            movement_types[mtype] = movement_types.get(mtype, 0) + 1
            movements_list.append({
                "id": m["id"],
                "item_name": m["item_name"],
                "movement_type": mtype,
                "quantity": float(m["quantity"]),
                "unit": m["unit"],
                "movement_date": _format_date(m["movement_date"]),
                "crop_name": m.get("crop_name"),
                "farm_name": m.get("farm_name"),
                "reason": m.get("reason") or ""
            })

        return jsonify({
            "status": "success",
            "report_type": "inventory",
            "filters": {
                "preset": flt["preset"],
                "range_label": flt["range_label"],
                "start_date": flt["start_date_str"],
                "end_date": flt["end_date_str"]
            },
            "data": {
                "total_items": total_items,
                "total_valuation": round(total_valuation, 2),
                "low_stock_count": low_stock_count,
                "out_of_stock_count": out_of_stock_count,
                "expiring_soon_count": expiring_count,
                "expired_count": expired_count,
                "category_breakdown": category_breakdown,
                "status_breakdown": status_breakdown,
                "movement_type_distribution": movement_types,
                "items_list": items_list,
                "movements_list": movements_list
            }
        }), 200

    except Exception as e:
        print(f"Error generating inventory report: {e}")
        return jsonify({"status": "error", "message": "Failed to generate inventory report."}), 500
    finally:
        if conn:
            conn.close()


# =============================================================================
# 8. ALERTS & NOTIFICATIONS REPORT
# =============================================================================

@reports_bp.route("/alerts", methods=["GET"])
def get_alerts_report():
    """Alerts & Notifications Report: volume by category, severity distribution & logs."""
    user_id, err = _authenticate()
    if err:
        return err

    flt = _parse_common_filters()
    start_d = flt["start_date"]
    end_d = flt["end_date"]

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = "SELECT * FROM notifications WHERE user_id = %s"
        params = [user_id]
        if start_d and end_d:
            query += " AND DATE(created_at) >= %s AND DATE(created_at) <= %s"
            params.extend([start_d, end_d])

        query += " ORDER BY created_at DESC, id DESC LIMIT 100"
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall() or []

        total_alerts = len(rows)
        unread_count = sum(1 for r in rows if not r.get("is_read"))
        read_count = total_alerts - unread_count

        category_counts = {}
        severity_counts = {"urgent": 0, "warning": 0, "info": 0}
        alerts_list = []

        for r in rows:
            cat = r.get("category") or "system"
            category_counts[cat] = category_counts.get(cat, 0) + 1

            sev = r.get("severity") or "info"
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

            alerts_list.append({
                "id": r["id"],
                "category": cat,
                "title": r["title"],
                "message": r["message"],
                "severity": sev,
                "is_read": bool(r.get("is_read")),
                "created_at": _format_date(r.get("created_at"))
            })

        return jsonify({
            "status": "success",
            "report_type": "alerts",
            "filters": {
                "preset": flt["preset"],
                "range_label": flt["range_label"],
                "start_date": flt["start_date_str"],
                "end_date": flt["end_date_str"]
            },
            "data": {
                "total_alerts": total_alerts,
                "unread_count": unread_count,
                "read_count": read_count,
                "category_distribution": category_counts,
                "severity_distribution": severity_counts,
                "alerts_list": alerts_list
            }
        }), 200

    except Exception as e:
        print(f"Error generating alerts report: {e}")
        return jsonify({"status": "error", "message": "Failed to generate alerts report."}), 500
    finally:
        if conn:
            conn.close()
