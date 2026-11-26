"""AgriSmart - Smart Crop Planning Foundation Backend Routes (Feature Upgrade 9 - Prompt 1)

Provides secure, parameterized CRUD operations and dashboards for seasonal crop planning:
- List & Filter Crop Plans (by season, year, status, farm)
- Upcoming Crop Plans for Dashboard Integration
- High-level Seasonal Planning KPI Summaries
- Create, Read, Update, Delete Crop Plans
- Form Context for Farm and Crop Dropdowns
"""

import calendar
from datetime import date, datetime, timedelta
from flask import Blueprint, jsonify, request

from config import get_db_connection
from utils.auth_tokens import get_user_id_from_token
from utils.crop_rotation_engine import analyze_all_farmer_farms
from utils.seasonal_crop_advisor import generate_seasonal_crop_recommendations
from utils.crop_reminder_engine import (
    generate_reminders_for_plan,
    generate_reminders_for_all_plans,
    get_farmer_reminders,
    update_reminder_status,
    add_reminder_to_farm_activities,
    get_or_create_reminder_settings,
    update_reminder_settings
)

crop_plan_bp = Blueprint("crop_plans", __name__, url_prefix="/api/crop-plans")

VALID_SEASONS = ["Kharif", "Rabi", "Zaid", "Year-round"]
SEASON_LOOKUP = {
    "kharif": "Kharif",
    "monsoon": "Kharif",
    "rabi": "Rabi",
    "winter": "Rabi",
    "zaid": "Zaid",
    "summer": "Zaid",
    "year-round": "Year-round",
    "perennial": "Year-round",
    "all-season": "Year-round",
}

VALID_STATUSES = ["Draft", "Planned", "In Progress", "Completed", "Cancelled"]
STATUS_LOOKUP = {
    "draft": "Draft",
    "planned": "Planned",
    "in progress": "In Progress",
    "in-progress": "In Progress",
    "inprogress": "In Progress",
    "active": "In Progress",
    "completed": "Completed",
    "done": "Completed",
    "cancelled": "Cancelled",
    "canceled": "Cancelled",
}

AREA_UNIT_LOOKUP = {
    "acre": "Acres",
    "acres": "Acres",
    "hectare": "Hectares",
    "hectares": "Hectares",
    "bigha": "Bigha",
    "bighas": "Bigha",
    "guntha": "Guntha",
    "gunthas": "Guntha",
    "sq meter": "Sq Meters",
    "sq meters": "Sq Meters",
}

VALID_AREA_UNITS = ["Acres", "Hectares", "Bigha", "Guntha", "Sq Meters"]


# =============================================================================
# HELPER FUNCTIONS
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


def _format_plan_row(row):
    """Format database row into a structured, JSON-serializable crop plan object."""
    sowing_date_val = row.get("planned_sowing_date")
    harvest_date_val = row.get("expected_harvest_date")

    today = date.today()
    days_until_sowing = None
    crop_duration_days = None

    if sowing_date_val:
        if isinstance(sowing_date_val, str):
            try:
                sowing_date_val = datetime.strptime(sowing_date_val[:10], "%Y-%m-%d").date()
            except ValueError:
                pass
        if isinstance(sowing_date_val, (date, datetime)):
            days_until_sowing = (sowing_date_val - today).days

    if sowing_date_val and harvest_date_val:
        if isinstance(harvest_date_val, str):
            try:
                harvest_date_val = datetime.strptime(harvest_date_val[:10], "%Y-%m-%d").date()
            except ValueError:
                pass
        if isinstance(sowing_date_val, (date, datetime)) and isinstance(harvest_date_val, (date, datetime)):
            crop_duration_days = (harvest_date_val - sowing_date_val).days

    status_val = row.get("status") or "Planned"
    is_upcoming = (days_until_sowing is not None and days_until_sowing >= 0 and status_val in ("Draft", "Planned"))

    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "farm_id": row.get("farm_id"),
        "farm_name": row.get("farm_name") or "Unassigned Farm",
        "farm_location": row.get("farm_location") or "",
        "crop_name": row["crop_name"],
        "variety": row.get("variety") or "",
        "season": row.get("season") or "Kharif",
        "planning_year": row.get("planning_year") or today.year,
        "planned_sowing_date": _format_date(row.get("planned_sowing_date")),
        "expected_harvest_date": _format_date(row.get("expected_harvest_date")),
        "land_area": float(row.get("land_area") or 0.0),
        "area_unit": row.get("area_unit") or "acre",
        "field_location": row.get("field_location") or "",
        "target_yield": float(row["target_yield"]) if row.get("target_yield") is not None else None,
        "yield_unit": row.get("yield_unit") or "quintal",
        "estimated_budget": float(row["estimated_budget"]) if row.get("estimated_budget") is not None else None,
        "estimated_revenue": float(row["estimated_revenue"]) if row.get("estimated_revenue") is not None else None,
        "status": status_val,
        "notes": row.get("notes") or "",
        "days_until_sowing": days_until_sowing,
        "crop_duration_days": crop_duration_days,
        "is_upcoming": is_upcoming,
        "created_at": str(row.get("created_at") or "")[:19],
        "updated_at": str(row.get("updated_at") or "")[:19],
    }


def _validate_crop_plan_payload(data, is_update=False):
    """Validate and sanitize input payload for create/update crop plan."""
    errors = {}

    crop_name = data.get("crop_name")
    if not is_update or "crop_name" in data:
        if not crop_name or not str(crop_name).strip():
            errors["crop_name"] = "Crop name is required."
        elif len(str(crop_name).strip()) > 100:
            errors["crop_name"] = "Crop name must not exceed 100 characters."

    season_raw = data.get("season")
    if not is_update or "season" in data:
        if not season_raw or not str(season_raw).strip():
            errors["season"] = "Season is required (Kharif, Rabi, Zaid, Year-round)."
        else:
            s_norm = SEASON_LOOKUP.get(str(season_raw).strip().lower())
            if not s_norm:
                errors["season"] = f"Invalid season. Allowed values: {', '.join(VALID_SEASONS)}."

    sowing_date = None
    if not is_update or "planned_sowing_date" in data:
        s_date_str = str(data.get("planned_sowing_date") or "").strip()
        if not s_date_str:
            errors["planned_sowing_date"] = "Planned sowing date is required."
        else:
            try:
                sowing_date = datetime.strptime(s_date_str[:10], "%Y-%m-%d").date()
            except ValueError:
                errors["planned_sowing_date"] = "Planned sowing date must be in YYYY-MM-DD format."

    harvest_date = None
    if not is_update or "expected_harvest_date" in data:
        h_date_str = str(data.get("expected_harvest_date") or "").strip()
        if h_date_str and h_date_str.lower() != "none" and h_date_str.lower() != "null":
            try:
                harvest_date = datetime.strptime(h_date_str[:10], "%Y-%m-%d").date()
            except ValueError:
                errors["expected_harvest_date"] = "Expected harvest date must be in YYYY-MM-DD format."

    if sowing_date and harvest_date and harvest_date < sowing_date:
        errors["expected_harvest_date"] = "Expected harvest date cannot be earlier than planned sowing date."

    if not is_update or "land_area" in data:
        area_raw = data.get("land_area")
        if area_raw is not None and str(area_raw).strip() != "" and str(area_raw).lower() != "none" and str(area_raw).lower() != "null":
            try:
                area_val = float(area_raw)
                if area_val <= 0:
                    errors["land_area"] = "Land area must be greater than 0."
            except (TypeError, ValueError):
                errors["land_area"] = "Land area must be a valid positive number."

    if "area_unit" in data and data["area_unit"]:
        u = str(data["area_unit"]).strip().lower()
        if u not in AREA_UNIT_LOOKUP:
            errors["area_unit"] = f"Invalid area unit. Allowed: {', '.join(VALID_AREA_UNITS)}."

    if "status" in data and data["status"]:
        st = str(data["status"]).strip().lower()
        if st not in STATUS_LOOKUP:
            errors["status"] = f"Invalid status. Allowed: {', '.join(VALID_STATUSES)}."

    return errors


# =============================================================================
# ENDPOINTS
# =============================================================================

@crop_plan_bp.route("/form-context", methods=["GET"])
def get_crop_planning_context():
    """Retrieve farmer's registered farms and common crops for form selection."""
    user_id, err = _authenticate()
    if err:
        return err

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Registered farms
        cursor.execute("""
            SELECT id, farm_name, location, total_area, area_unit
            FROM farms
            WHERE user_id = %s
            ORDER BY farm_name ASC
        """, (user_id,))
        farms = cursor.fetchall() or []

        # 2. Distinct crop names farmer has used
        cursor.execute("""
            SELECT DISTINCT crop_name
            FROM crops
            WHERE user_id = %s AND crop_name IS NOT NULL AND crop_name != ''
            ORDER BY crop_name ASC
        """, (user_id,))
        farmer_crops = [r["crop_name"] for r in (cursor.fetchall() or [])]

        # Standard Indian crops list
        standard_crops = [
            "Wheat", "Rice / Paddy", "Cotton", "Soybean", "Sugarcane",
            "Maize", "Tomato", "Onion", "Potato", "Gram / Chana",
            "Groundnut", "Mustard", "Bajra / Pearl Millet", "Jowar / Sorghum",
            "Tur / Arhar", "Moong / Green Gram", "Chilli", "Turmeric", "Ginger"
        ]

        all_crops = sorted(list(set(farmer_crops + standard_crops)))

        return jsonify({
            "status": "success",
            "farms": farms,
            "crops": all_crops,
            "seasons": VALID_SEASONS,
            "statuses": VALID_STATUSES,
            "area_units": VALID_AREA_UNITS
        }), 200

    except Exception as e:
        print(f"Error fetching crop plan form context: {e}")
        return jsonify({"status": "error", "message": "Failed to load crop planning context."}), 500
    finally:
        if conn:
            conn.close()


@crop_plan_bp.route("", methods=["GET"])
def get_crop_plans():
    """
    List crop plans for authenticated farmer with optional filtering.
    Filters: season, year, status, farm_id.
    """
    user_id, err = _authenticate()
    if err:
        return err

    season_filter = request.args.get("season", "").strip()
    year_filter = request.args.get("year", "").strip()
    status_filter = request.args.get("status", "").strip()
    farm_id_filter = request.args.get("farm_id", "").strip()
    sort_by = request.args.get("sort_by", "sowing_date").strip().lower()
    order = request.args.get("order", "asc").strip().upper()

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT cp.*, f.farm_name, f.location AS farm_location
            FROM crop_plans cp
            LEFT JOIN farms f ON cp.farm_id = f.id
            WHERE cp.user_id = %s
        """
        params = [user_id]

        if season_filter and season_filter.lower() != "all":
            norm_season = SEASON_LOOKUP.get(season_filter.lower(), season_filter)
            query += " AND cp.season = %s"
            params.append(norm_season)

        if year_filter and year_filter.isdigit():
            query += " AND cp.planning_year = %s"
            params.append(int(year_filter))

        if status_filter and status_filter.lower() != "all":
            norm_status = STATUS_LOOKUP.get(status_filter.lower(), status_filter)
            query += " AND cp.status = %s"
            params.append(norm_status)

        if farm_id_filter and farm_id_filter.lower() != "all" and farm_id_filter.isdigit():
            query += " AND cp.farm_id = %s"
            params.append(int(farm_id_filter))

        # Safe sorting column mapping
        sort_col_map = {
            "sowing_date": "cp.planned_sowing_date",
            "harvest_date": "cp.expected_harvest_date",
            "crop_name": "cp.crop_name",
            "created_at": "cp.created_at",
            "land_area": "cp.land_area",
        }
        order_col = sort_col_map.get(sort_by, "cp.planned_sowing_date")
        order_dir = "DESC" if order == "DESC" else "ASC"
        query += f" ORDER BY {order_col} {order_dir}, cp.id ASC"

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall() or []

        plans = [_format_plan_row(r) for r in rows]

        return jsonify({
            "status": "success",
            "total_plans": len(plans),
            "plans": plans
        }), 200

    except Exception as e:
        print(f"Error fetching crop plans: {e}")
        return jsonify({"status": "error", "message": "Failed to fetch crop plans."}), 500
    finally:
        if conn:
            conn.close()


@crop_plan_bp.route("/upcoming", methods=["GET"])
def get_upcoming_crop_plans():
    """Retrieve upcoming and active crop plans for dashboard display."""
    user_id, err = _authenticate()
    if err:
        return err

    limit_param = request.args.get("limit", "5").strip()
    limit = int(limit_param) if limit_param.isdigit() else 5

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        today = date.today()
        # Look from 7 days ago to future sowings
        min_date = today - date.resolution * 7

        query = """
            SELECT cp.*, f.farm_name, f.location AS farm_location
            FROM crop_plans cp
            LEFT JOIN farms f ON cp.farm_id = f.id
            WHERE cp.user_id = %s
              AND cp.status IN ('Draft', 'Planned', 'In Progress')
              AND cp.planned_sowing_date >= %s
            ORDER BY cp.planned_sowing_date ASC
            LIMIT %s
        """
        cursor.execute(query, (user_id, min_date, limit))
        rows = cursor.fetchall() or []

        plans = [_format_plan_row(r) for r in rows]

        return jsonify({
            "status": "success",
            "count": len(plans),
            "plans": plans,
            "upcoming_plans": plans
        }), 200

    except Exception as e:
        print(f"Error fetching upcoming crop plans: {e}")
        return jsonify({"status": "error", "message": "Failed to fetch upcoming crop plans."}), 500
    finally:
        if conn:
            conn.close()


@crop_plan_bp.route("/summary", methods=["GET"])
def get_crop_planning_summary():
    """Retrieve high-level KPIs and seasonal performance across crop plans."""
    user_id, err = _authenticate()
    if err:
        return err

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                COUNT(*) AS total_plans,
                SUM(CASE WHEN status IN ('Draft', 'Planned') THEN 1 ELSE 0 END) AS planned_count,
                SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) AS in_progress_count,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed_count,
                SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END) AS cancelled_count,
                COALESCE(SUM(land_area), 0.0) AS total_planned_area,
                COALESCE(SUM(estimated_budget), 0.0) AS total_estimated_budget,
                COALESCE(SUM(estimated_revenue), 0.0) AS total_estimated_revenue
            FROM crop_plans
            WHERE user_id = %s
        """, (user_id,))
        sum_row = cursor.fetchone() or {}

        # Seasonal distribution
        cursor.execute("""
            SELECT season, COUNT(*) AS count, COALESCE(SUM(land_area), 0.0) AS area
            FROM crop_plans
            WHERE user_id = %s
            GROUP BY season
        """, (user_id,))
        season_rows = cursor.fetchall() or []
        season_breakdown = {r["season"]: {"count": int(r["count"]), "area": float(r["area"])} for r in season_rows}

        # Nearest upcoming plan
        today = date.today()
        cursor.execute("""
            SELECT cp.*, f.farm_name, f.location AS farm_location
            FROM crop_plans cp
            LEFT JOIN farms f ON cp.farm_id = f.id
            WHERE cp.user_id = %s AND cp.status IN ('Draft', 'Planned') AND cp.planned_sowing_date >= %s
            ORDER BY cp.planned_sowing_date ASC
            LIMIT 1
        """, (user_id, today))
        next_row = cursor.fetchone()
        next_plan = _format_plan_row(next_row) if next_row else None

        return jsonify({
            "status": "success",
            "summary": {
                "total_plans": int(sum_row.get("total_plans") or 0),
                "planned_count": int(sum_row.get("planned_count") or 0),
                "in_progress_count": int(sum_row.get("in_progress_count") or 0),
                "completed_count": int(sum_row.get("completed_count") or 0),
                "cancelled_count": int(sum_row.get("cancelled_count") or 0),
                "total_planned_area": float(sum_row.get("total_planned_area") or 0.0),
                "total_estimated_budget": float(sum_row.get("total_estimated_budget") or 0.0),
                "total_estimated_revenue": float(sum_row.get("total_estimated_revenue") or 0.0),
                "season_breakdown": season_breakdown,
                "next_sowing_plan": next_plan
            }
        }), 200

    except Exception as e:
        print(f"Error fetching crop plan summary: {e}")
        return jsonify({"status": "error", "message": "Failed to load crop plan summary."}), 500
    finally:
        if conn:
            conn.close()


@crop_plan_bp.route("/rotation-analysis", methods=["GET"])
def get_crop_rotation_analysis():
    """Analyze crop rotation patterns, repeated crop families, and legume suggestions per farm."""
    user_id, err = _authenticate()
    if err:
        return err

    farm_id_param = request.args.get("farm_id")
    farm_id = None
    if farm_id_param and farm_id_param.strip() and farm_id_param.strip().lower() != "all":
        if farm_id_param.strip().isdigit():
            farm_id = int(farm_id_param.strip())

    try:
        analyses = analyze_all_farmer_farms(user_id=user_id, farm_id=farm_id)
        return jsonify({
            "status": "success",
            "farm_analyses": analyses,
            "total_farms_analyzed": len(analyses)
        }), 200
    except Exception as e:
        print(f"Error analyzing crop rotation: {e}")
        return jsonify({"status": "error", "message": "Failed to analyze crop rotation patterns."}), 500


@crop_plan_bp.route("/recommendations", methods=["GET"])
def get_crop_recommendations():
    """Retrieve seasonal and soil-aware crop recommendations for authenticated farmer."""
    user_id, err = _authenticate()
    if err:
        return err

    farm_id_param = request.args.get("farm_id")
    farm_id = int(farm_id_param.strip()) if farm_id_param and farm_id_param.strip().isdigit() else None
    season_param = request.args.get("season")
    soil_override = request.args.get("soil_type")
    limit_param = request.args.get("limit", "15")
    limit = int(limit_param.strip()) if limit_param and limit_param.strip().isdigit() else 15

    try:
        rec_data = generate_seasonal_crop_recommendations(
            user_id=user_id,
            farm_id=farm_id,
            season=season_param,
            soil_override=soil_override,
            limit=limit
        )
        if rec_data.get("status") == "error":
            return jsonify(rec_data), rec_data.get("code", 400)
        return jsonify(rec_data), 200
    except Exception as e:
        print(f"Error generating crop recommendations: {e}")
        return jsonify({"status": "error", "message": "Failed to generate seasonal crop recommendations."}), 500


@crop_plan_bp.route("/calendar", methods=["GET"])
def get_crop_calendar():
    """
    Retrieve crop calendar events and plans grouped by day for month or week views.
    Supports date-range filtering, farm_id, season, crop, and status filters with JWT tenant isolation.
    """
    user_id, err = _authenticate()
    if err:
        return err

    today = date.today()
    view = request.args.get("view", "month").strip().lower()
    if view not in ("month", "week"):
        view = "month"

    start_date_str = request.args.get("start_date", "").strip()
    end_date_str = request.args.get("end_date", "").strip()

    start_dt = None
    end_dt = None
    year = today.year
    month = today.month

    if start_date_str and end_date_str:
        try:
            start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            if start_dt > end_dt:
                return jsonify({"status": "error", "message": "start_date cannot be after end_date."}), 400
            # Safety limit: max 366 days
            if (end_dt - start_dt).days > 366:
                return jsonify({"status": "error", "message": "Date range cannot exceed 366 days."}), 400
            year = start_dt.year
            month = start_dt.month
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid date format. Expected YYYY-MM-DD."}), 400
    else:
        # Determine year and month from query or default
        try:
            year = int(request.args.get("year", today.year))
            month = int(request.args.get("month", today.month))
            if month < 1 or month > 12:
                month = today.month
        except (ValueError, TypeError):
            year = today.year
            month = today.month

        if view == "week":
            # Week view based on reference date
            ref_date_param = request.args.get("date", "").strip()
            if ref_date_param:
                try:
                    ref_dt = datetime.strptime(ref_date_param, "%Y-%m-%d").date()
                except ValueError:
                    ref_dt = today
            else:
                try:
                    day_param = int(request.args.get("day", today.day if (year == today.year and month == today.month) else 1))
                    num_days_in_month = calendar.monthrange(year, month)[1]
                    day_param = max(1, min(num_days_in_month, day_param))
                    ref_dt = date(year, month, day_param)
                except (ValueError, TypeError):
                    ref_dt = today

            # Monday as start of week (weekday() 0=Mon, 6=Sun)
            start_dt = ref_dt - timedelta(days=ref_dt.weekday())
            end_dt = start_dt + timedelta(days=6)
        else:
            # Month view
            num_days = calendar.monthrange(year, month)[1]
            start_dt = date(year, month, 1)
            end_dt = date(year, month, num_days)

    farm_id_filter = request.args.get("farm_id", "").strip()
    season_filter = request.args.get("season", "").strip()
    crop_filter = request.args.get("crop", "").strip()
    status_filter = request.args.get("status", "").strip()

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT cp.*, f.farm_name, f.location AS farm_location
            FROM crop_plans cp
            LEFT JOIN farms f ON cp.farm_id = f.id
            WHERE cp.user_id = %s
              AND cp.planned_sowing_date <= %s
              AND cp.expected_harvest_date >= %s
        """
        params = [user_id, end_dt.strftime("%Y-%m-%d"), start_dt.strftime("%Y-%m-%d")]

        if farm_id_filter and farm_id_filter.lower() != "all" and farm_id_filter.isdigit():
            query += " AND cp.farm_id = %s"
            params.append(int(farm_id_filter))

        if season_filter and season_filter.lower() != "all":
            norm_season = SEASON_LOOKUP.get(season_filter.lower(), season_filter)
            query += " AND cp.season = %s"
            params.append(norm_season)

        if crop_filter and crop_filter.lower() != "all":
            query += " AND (cp.crop_name LIKE %s OR cp.variety LIKE %s)"
            params.extend([f"%{crop_filter}%", f"%{crop_filter}%"])

        if status_filter and status_filter.lower() != "all":
            norm_status = STATUS_LOOKUP.get(status_filter.lower(), status_filter)
            query += " AND cp.status = %s"
            params.append(norm_status)

        query += " ORDER BY cp.planned_sowing_date ASC, cp.id ASC"

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall() or []

        plans = [_format_plan_row(r) for r in rows]

        # Fetch reminders in date range
        reminders_by_date = {}
        total_reminders_count = 0
        pending_reminders_count = 0
        try:
            cursor.execute("""
                SELECT r.id, r.crop_plan_id, r.farm_id, r.reminder_type, r.milestone_type,
                       r.title, r.description, r.guidance, r.due_date, r.days_offset,
                       r.status, r.is_estimated,
                       p.crop_name, p.variety, p.season, f.farm_name
                FROM crop_plan_reminders r
                JOIN crop_plans p ON p.id = r.crop_plan_id
                LEFT JOIN farms f ON f.id = r.farm_id
                WHERE r.user_id = %s AND r.due_date BETWEEN %s AND %s
                ORDER BY r.due_date ASC, r.id ASC
            """, (user_id, start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")))
            rem_rows = cursor.fetchall() or []
            for rr in rem_rows:
                d_str = rr["due_date"].strftime("%Y-%m-%d") if isinstance(rr["due_date"], date) else str(rr["due_date"])[:10]
                if d_str not in reminders_by_date:
                    reminders_by_date[d_str] = []
                icon = "🌱" if rr["milestone_type"] == "sowing" else ("🌾" if rr["milestone_type"] == "harvest" else "⏰")
                reminders_by_date[d_str].append({
                    "id": rr["id"],
                    "plan_id": rr["crop_plan_id"],
                    "crop_name": rr["crop_name"],
                    "variety": rr.get("variety"),
                    "season": rr.get("season"),
                    "farm_name": rr.get("farm_name"),
                    "title": rr["title"],
                    "description": rr.get("description"),
                    "guidance": rr.get("guidance"),
                    "milestone_type": rr["milestone_type"],
                    "reminder_type": rr["reminder_type"],
                    "status": rr["status"],
                    "is_estimated": bool(rr.get("is_estimated")),
                    "due_date": d_str,
                    "icon": icon
                })
                total_reminders_count += 1
                if rr["status"] == "pending":
                    pending_reminders_count += 1
        except Exception as rem_err:
            print(f"Warning: could not fetch calendar reminders: {rem_err}")

        # Build day map for every date in [start_dt, end_dt]
        days_list = []
        cur = start_dt
        total_sowing_events = 0
        total_harvest_events = 0
        active_growing_plans = set()

        while cur <= end_dt:
            cur_str = cur.strftime("%Y-%m-%d")
            sowing_items = []
            harvest_items = []
            growing_items = []

            for p in plans:
                p_sow = datetime.strptime(p["planned_sowing_date"], "%Y-%m-%d").date() if p.get("planned_sowing_date") else None
                p_har = datetime.strptime(p["expected_harvest_date"], "%Y-%m-%d").date() if p.get("expected_harvest_date") else None

                if not p_sow or not p_har:
                    continue

                if cur == p_sow:
                    sowing_items.append({
                        "plan_id": p["id"],
                        "crop_name": p["crop_name"],
                        "variety": p.get("variety"),
                        "season": p["season"],
                        "status": p["status"],
                        "farm_name": p.get("farm_name"),
                        "land_area": p.get("land_area"),
                        "area_unit": p.get("area_unit"),
                        "event_type": "sowing",
                        "date": cur_str,
                        "label": f"Sowing: {p['crop_name']}",
                        "icon": "🌱"
                    })
                    total_sowing_events += 1

                if cur == p_har:
                    harvest_items.append({
                        "plan_id": p["id"],
                        "crop_name": p["crop_name"],
                        "variety": p.get("variety"),
                        "season": p["season"],
                        "status": p["status"],
                        "farm_name": p.get("farm_name"),
                        "land_area": p.get("land_area"),
                        "area_unit": p.get("area_unit"),
                        "event_type": "harvest",
                        "date": cur_str,
                        "label": f"Harvest: {p['crop_name']}",
                        "icon": "🌾"
                    })
                    total_harvest_events += 1

                if p_sow < cur < p_har:
                    growing_items.append({
                        "plan_id": p["id"],
                        "crop_name": p["crop_name"],
                        "variety": p.get("variety"),
                        "season": p["season"],
                        "status": p["status"],
                        "farm_name": p.get("farm_name"),
                        "land_area": p.get("land_area"),
                        "area_unit": p.get("area_unit"),
                        "event_type": "growing",
                        "date": cur_str,
                        "sowing_date": p["planned_sowing_date"],
                        "harvest_date": p["expected_harvest_date"],
                        "days_growing": (cur - p_sow).days,
                        "total_duration": (p_har - p_sow).days,
                        "progress_pct": round(((cur - p_sow).days / max(1, (p_har - p_sow).days)) * 100),
                        "label": f"Growing: {p['crop_name']}",
                        "icon": "🌿"
                    })
                    active_growing_plans.add(p["id"])

            day_rems = reminders_by_date.get(cur_str, [])

            days_list.append({
                "date": cur_str,
                "day": cur.day,
                "month": cur.month,
                "year": cur.year,
                "weekday": cur.weekday(),  # 0=Monday, 6=Sunday
                "is_today": (cur == today),
                "is_current_month": (cur.month == month),
                "sowing_events": sowing_items,
                "harvest_events": harvest_items,
                "growing_crops": growing_items,
                "reminders": day_rems,
                "reminder_count": len(day_rems),
                "has_pending_reminders": any(r["status"] == "pending" for r in day_rems),
                "total_events": len(sowing_items) + len(harvest_items),
                "total_active": len(sowing_items) + len(harvest_items) + len(growing_items)
            })

            cur += timedelta(days=1)

        month_name = calendar.month_name[month] if (1 <= month <= 12) else ""

        return jsonify({
            "status": "success",
            "view": view,
            "start_date": start_dt.strftime("%Y-%m-%d"),
            "end_date": end_dt.strftime("%Y-%m-%d"),
            "year": year,
            "month": month,
            "month_name": month_name,
            "total_plans": len(plans),
            "plans": plans,
            "days": days_list,
            "summary": {
                "total_plans": len(plans),
                "sowing_events": total_sowing_events,
                "harvest_events": total_harvest_events,
                "growing_crops": len(active_growing_plans),
                "total_reminders": total_reminders_count,
                "pending_reminders": pending_reminders_count
            }
        }), 200

    except Exception as e:
        print(f"Error fetching crop calendar: {e}")
        return jsonify({"status": "error", "message": "Failed to fetch crop calendar."}), 500
    finally:
        if conn:
            conn.close()


# =============================================================================
# SMART CROP REMINDER ROUTES (Feature Upgrade 9 - Phase 3 Part 2)
# =============================================================================

@crop_plan_bp.route("/reminders", methods=["GET"])
def get_crop_reminders():
    """
    Retrieve reminders for the authenticated farmer with multi-factor filtering:
    - status: 'all', 'upcoming', 'today', 'overdue', 'pending', 'completed', 'dismissed'
    - type: 'all', 'milestone', 'growth_stage'
    - plan_id, farm_id, limit, start_date, end_date
    Automatically ensures reminders are generated/synced for all active plans.
    """
    user_id, err = _authenticate()
    if err:
        return err

    conn = None
    try:
        conn = get_db_connection()
        # Automatically synchronize reminders for user's plans
        generate_reminders_for_all_plans(user_id, conn)

        filters = {
            "status": request.args.get("status", "all"),
            "type": request.args.get("type", "all"),
            "plan_id": request.args.get("plan_id"),
            "farm_id": request.args.get("farm_id"),
            "limit": request.args.get("limit"),
            "start_date": request.args.get("start_date"),
            "end_date": request.args.get("end_date")
        }

        res = get_farmer_reminders(user_id, conn, filters)
        return jsonify({
            "status": "success",
            "reminders": res["reminders"],
            "counts": res["counts"],
            "total_returned": res["total_returned"]
        }), 200

    except Exception as e:
        print(f"Error fetching crop reminders: {e}")
        return jsonify({"status": "error", "message": "Failed to fetch crop reminders."}), 500
    finally:
        if conn:
            conn.close()


@crop_plan_bp.route("/reminders/settings", methods=["GET"])
def get_reminder_settings():
    """Retrieve farmer's reminder configuration."""
    user_id, err = _authenticate()
    if err:
        return err

    conn = None
    try:
        conn = get_db_connection()
        settings = get_or_create_reminder_settings(user_id, conn)
        return jsonify({"status": "success", "settings": settings}), 200
    except Exception as e:
        print(f"Error fetching reminder settings: {e}")
        return jsonify({"status": "error", "message": "Failed to fetch reminder settings."}), 500
    finally:
        if conn:
            conn.close()


@crop_plan_bp.route("/reminders/settings", methods=["PUT"])
def save_reminder_settings():
    """Update farmer's reminder configuration and synchronize plan reminders."""
    user_id, err = _authenticate()
    if err:
        return err

    payload = request.get_json(silent=True) or {}

    conn = None
    try:
        conn = get_db_connection()
        updated = update_reminder_settings(user_id, payload, conn)
        # Re-generate reminders with new configuration
        gen_res = generate_reminders_for_all_plans(user_id, conn)
        return jsonify({
            "status": "success",
            "message": "Reminder settings updated successfully.",
            "settings": updated,
            "regenerated": gen_res
        }), 200
    except Exception as e:
        print(f"Error updating reminder settings: {e}")
        return jsonify({"status": "error", "message": "Failed to update reminder settings."}), 500
    finally:
        if conn:
            conn.close()


@crop_plan_bp.route("/<int:plan_id>/generate-reminders", methods=["POST"])
def trigger_plan_reminders(plan_id):
    """Force generate or refresh reminders for a specific plan."""
    user_id, err = _authenticate()
    if err:
        return err

    payload = request.get_json(silent=True) or {}

    conn = None
    try:
        conn = get_db_connection()
        custom_settings = None
        if payload:
            custom_settings = {
                "sowing_lead_days": payload.get("sowing_lead_days", [7, 1, 0]),
                "harvest_lead_days": payload.get("harvest_lead_days", [14, 7, 0]),
                "enable_growth_stages": payload.get("enable_growth_stages", True)
            }
        res = generate_reminders_for_plan(user_id, plan_id, conn, custom_settings)
        return jsonify({
            "status": "success",
            "message": f"Reminders processed for crop plan #{plan_id}.",
            "result": res
        }), 200
    except Exception as e:
        print(f"Error generating reminders for plan #{plan_id}: {e}")
        return jsonify({"status": "error", "message": "Failed to generate reminders."}), 500
    finally:
        if conn:
            conn.close()


@crop_plan_bp.route("/reminders/<int:reminder_id>/status", methods=["PATCH"])
def patch_reminder_status(reminder_id):
    """Update status of a reminder ('completed', 'dismissed', 'pending')."""
    user_id, err = _authenticate()
    if err:
        return err

    payload = request.get_json(silent=True) or {}
    new_status = payload.get("status")
    if not new_status:
        return jsonify({"status": "error", "message": "Missing 'status' in request body."}), 400

    conn = None
    try:
        conn = get_db_connection()
        res = update_reminder_status(user_id, reminder_id, new_status, conn)
        status_code = res.get("code", 200 if res["status"] == "success" else 400)
        return jsonify(res), status_code
    except Exception as e:
        print(f"Error updating reminder status: {e}")
        return jsonify({"status": "error", "message": "Failed to update reminder status."}), 500
    finally:
        if conn:
            conn.close()


@crop_plan_bp.route("/reminders/<int:reminder_id>/add-to-activity", methods=["POST"])
def add_reminder_activity(reminder_id):
    """Convert a crop reminder into a Farm Activity."""
    user_id, err = _authenticate()
    if err:
        return err

    conn = None
    try:
        conn = get_db_connection()
        res = add_reminder_to_farm_activities(user_id, reminder_id, conn)
        status_code = res.get("code", 201 if (res["status"] == "success" and not res.get("already_existed")) else 200)
        return jsonify(res), status_code
    except Exception as e:
        print(f"Error adding reminder to farm activities: {e}")
        return jsonify({"status": "error", "message": "Failed to convert reminder to activity."}), 500
    finally:
        if conn:
            conn.close()


@crop_plan_bp.route("/<int:plan_id>", methods=["GET"])
def get_crop_plan_by_id(plan_id):
    """Retrieve detailed crop plan by ID with tenant data isolation."""
    user_id, err = _authenticate()
    if err:
        return err

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT cp.*, f.farm_name, f.location AS farm_location
            FROM crop_plans cp
            LEFT JOIN farms f ON cp.farm_id = f.id
            WHERE cp.user_id = %s AND cp.id = %s
        """, (user_id, plan_id))
        row = cursor.fetchone()

        if not row:
            return jsonify({"status": "error", "message": "Crop plan not found."}), 404

        return jsonify({
            "status": "success",
            "plan": _format_plan_row(row)
        }), 200

    except Exception as e:
        print(f"Error fetching crop plan {plan_id}: {e}")
        return jsonify({"status": "error", "message": "Failed to fetch crop plan."}), 500
    finally:
        if conn:
            conn.close()


@crop_plan_bp.route("", methods=["POST"])
def create_crop_plan():
    """Create a new seasonal crop plan for authenticated farmer."""
    user_id, err = _authenticate()
    if err:
        return err

    payload = request.get_json(silent=True) or {}
    errors = _validate_crop_plan_payload(payload, is_update=False)
    if errors:
        return jsonify({"status": "error", "message": "Validation failed.", "errors": errors}), 400

    farm_id = payload.get("farm_id")
    if farm_id and str(farm_id).lower() != "none" and str(farm_id).isdigit():
        farm_id = int(farm_id)
    else:
        farm_id = None

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Verify farm ownership if farm_id specified
        if farm_id:
            cursor.execute("SELECT id FROM farms WHERE id = %s AND user_id = %s", (farm_id, user_id))
            if not cursor.fetchone():
                return jsonify({"status": "error", "message": "Invalid farm selected. Please choose a farm you own."}), 400

        crop_name = str(payload["crop_name"]).strip()
        variety = str(payload.get("variety") or "").strip() or None
        season = SEASON_LOOKUP.get(str(payload["season"]).strip().lower(), "Kharif")

        sowing_date_str = str(payload["planned_sowing_date"]).strip()[:10]
        harvest_raw = payload.get("expected_harvest_date")
        harvest_date_str = str(harvest_raw).strip()[:10] if harvest_raw and str(harvest_raw).lower() not in ("none", "null", "") else None

        # Derive planning_year
        planning_year = payload.get("planning_year")
        if not planning_year or not str(planning_year).isdigit():
            planning_year = datetime.strptime(sowing_date_str, "%Y-%m-%d").year
        else:
            planning_year = int(planning_year)

        land_area = payload.get("land_area")
        land_area = float(land_area) if land_area not in (None, "") else None
        raw_unit = str(payload.get("area_unit") or "Acres").strip().lower()
        area_unit = AREA_UNIT_LOOKUP.get(raw_unit, "Acres")

        field_location = str(payload.get("field_location") or "").strip() or None

        target_yield = payload.get("target_yield")
        target_yield = float(target_yield) if target_yield not in (None, "") else None

        yield_unit = str(payload.get("yield_unit") or "quintal").strip() or "quintal"

        estimated_budget = payload.get("estimated_budget")
        estimated_budget = float(estimated_budget) if estimated_budget not in (None, "") else None

        estimated_revenue = payload.get("estimated_revenue")
        estimated_revenue = float(estimated_revenue) if estimated_revenue not in (None, "") else None

        status = STATUS_LOOKUP.get(str(payload.get("status") or "Planned").strip().lower(), "Planned")
        notes = str(payload.get("notes") or "").strip() or None

        insert_sql = """
            INSERT INTO crop_plans (
                user_id, farm_id, crop_name, variety, season, planning_year,
                planned_sowing_date, expected_harvest_date, land_area, area_unit,
                field_location, target_yield, yield_unit, estimated_budget, estimated_revenue,
                status, notes
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s
            )
        """
        cursor.execute(insert_sql, (
            user_id, farm_id, crop_name, variety, season, planning_year,
            sowing_date_str, harvest_date_str, land_area, area_unit,
            field_location, target_yield, yield_unit, estimated_budget, estimated_revenue,
            status, notes
        ))
        conn.commit()
        plan_id = cursor.lastrowid

        # Fetch and return inserted plan
        cursor.execute("""
            SELECT cp.*, f.farm_name, f.location AS farm_location
            FROM crop_plans cp
            LEFT JOIN farms f ON cp.farm_id = f.id
            WHERE cp.id = %s
        """, (plan_id,))
        created_row = cursor.fetchone()

        # Auto-generate milestone and growth reminders for the new plan
        try:
            generate_reminders_for_plan(user_id, plan_id, conn)
        except Exception as rem_gen_err:
            print(f"Warning: could not auto-generate reminders on plan creation: {rem_gen_err}")

        return jsonify({
            "status": "success",
            "message": "Crop plan created successfully.",
            "plan": _format_plan_row(created_row)
        }), 201

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error creating crop plan: {e}")
        return jsonify({"status": "error", "message": "Failed to create crop plan."}), 500
    finally:
        if conn:
            conn.close()


@crop_plan_bp.route("/<int:plan_id>", methods=["PUT"])
def update_crop_plan(plan_id):
    """Update an existing crop plan owned by authenticated farmer."""
    user_id, err = _authenticate()
    if err:
        return err

    payload = request.get_json(silent=True) or {}
    errors = _validate_crop_plan_payload(payload, is_update=True)
    if errors:
        return jsonify({"status": "error", "message": "Validation failed.", "errors": errors}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check existing plan ownership
        cursor.execute("SELECT * FROM crop_plans WHERE id = %s AND user_id = %s", (plan_id, user_id))
        existing = cursor.fetchone()
        if not existing:
            return jsonify({"status": "error", "message": "Crop plan not found or unauthorized."}), 404

        farm_id = payload.get("farm_id")
        if farm_id is not None:
            if str(farm_id).lower() in ("none", "", "null", "all"):
                farm_id = None
            elif str(farm_id).isdigit():
                farm_id = int(farm_id)
                cursor.execute("SELECT id FROM farms WHERE id = %s AND user_id = %s", (farm_id, user_id))
                if not cursor.fetchone():
                    return jsonify({"status": "error", "message": "Invalid farm selected."}), 400
        else:
            farm_id = existing["farm_id"]

        crop_name = str(payload.get("crop_name", existing["crop_name"])).strip()
        variety = str(payload.get("variety", existing["variety"]) or "").strip() or None

        season_raw = payload.get("season", existing["season"])
        season = SEASON_LOOKUP.get(str(season_raw).strip().lower(), existing["season"])

        sowing_val = payload.get("planned_sowing_date") or existing.get("planned_sowing_date")
        sowing_str = str(sowing_val).strip()[:10] if sowing_val else None

        harvest_val = payload.get("expected_harvest_date") if "expected_harvest_date" in payload else existing.get("expected_harvest_date")
        harvest_str = str(harvest_val).strip()[:10] if harvest_val and str(harvest_val).lower() not in ("none", "null", "") else None

        planning_year = payload.get("planning_year")
        if planning_year and str(planning_year).isdigit():
            planning_year = int(planning_year)
        else:
            planning_year = datetime.strptime(sowing_str, "%Y-%m-%d").year if sowing_str else datetime.now().year

        land_area = payload.get("land_area", existing["land_area"])
        land_area = float(land_area) if land_area not in (None, "") else None

        raw_unit = str(payload.get("area_unit", existing["area_unit"]) or "Acres").strip().lower()
        area_unit = AREA_UNIT_LOOKUP.get(raw_unit, existing.get("area_unit") or "Acres")

        field_location = str(payload.get("field_location", existing["field_location"]) or "").strip() or None

        target_yield = payload.get("target_yield") if "target_yield" in payload else existing["target_yield"]
        target_yield = float(target_yield) if target_yield not in (None, "") else None

        yield_unit = str(payload.get("yield_unit", existing["yield_unit"]) or "quintal").strip()

        estimated_budget = payload.get("estimated_budget") if "estimated_budget" in payload else existing["estimated_budget"]
        estimated_budget = float(estimated_budget) if estimated_budget not in (None, "") else None

        estimated_revenue = payload.get("estimated_revenue") if "estimated_revenue" in payload else existing["estimated_revenue"]
        estimated_revenue = float(estimated_revenue) if estimated_revenue not in (None, "") else None

        status_raw = payload.get("status", existing["status"])
        status = STATUS_LOOKUP.get(str(status_raw).strip().lower(), existing["status"])

        notes = str(payload.get("notes", existing["notes"]) or "").strip() or None

        update_sql = """
            UPDATE crop_plans SET
                farm_id = %s,
                crop_name = %s,
                variety = %s,
                season = %s,
                planning_year = %s,
                planned_sowing_date = %s,
                expected_harvest_date = %s,
                land_area = %s,
                area_unit = %s,
                field_location = %s,
                target_yield = %s,
                yield_unit = %s,
                estimated_budget = %s,
                estimated_revenue = %s,
                status = %s,
                notes = %s
            WHERE id = %s AND user_id = %s
        """
        cursor.execute(update_sql, (
            farm_id, crop_name, variety, season, planning_year,
            sowing_str, harvest_str, land_area, area_unit,
            field_location, target_yield, yield_unit, estimated_budget, estimated_revenue,
            status, notes,
            plan_id, user_id
        ))
        conn.commit()

        # Fetch updated plan
        cursor.execute("""
            SELECT cp.*, f.farm_name, f.location AS farm_location
            FROM crop_plans cp
            LEFT JOIN farms f ON cp.farm_id = f.id
            WHERE cp.id = %s
        """, (plan_id,))
        updated_row = cursor.fetchone()

        # Synchronize milestone and growth reminders for the updated plan
        try:
            generate_reminders_for_plan(user_id, plan_id, conn)
        except Exception as rem_sync_err:
            print(f"Warning: could not synchronize reminders on plan update: {rem_sync_err}")

        return jsonify({
            "status": "success",
            "message": "Crop plan updated successfully.",
            "plan": _format_plan_row(updated_row)
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error updating crop plan {plan_id}: {e}")
        return jsonify({"status": "error", "message": "Failed to update crop plan."}), 500
    finally:
        if conn:
            conn.close()


@crop_plan_bp.route("/<int:plan_id>", methods=["DELETE"])
def delete_crop_plan(plan_id):
    """Delete a crop plan owned by authenticated farmer."""
    user_id, err = _authenticate()
    if err:
        return err

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, crop_name FROM crop_plans WHERE id = %s AND user_id = %s", (plan_id, user_id))
        plan = cursor.fetchone()
        if not plan:
            return jsonify({"status": "error", "message": "Crop plan not found or unauthorized."}), 404

        cursor.execute("DELETE FROM crop_plans WHERE id = %s AND user_id = %s", (plan_id, user_id))
        conn.commit()

        return jsonify({
            "status": "success",
            "message": f"Crop plan for '{plan['crop_name']}' deleted successfully."
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error deleting crop plan {plan_id}: {e}")
        return jsonify({"status": "error", "message": "Failed to delete crop plan."}), 500
    finally:
        if conn:
            conn.close()
