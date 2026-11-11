import calendar
import re
from datetime import date, datetime, timedelta
from flask import Blueprint, jsonify, request
from config import get_db_connection
from utils.auth_tokens import get_user_id_from_token

activity_bp = Blueprint("activities", __name__, url_prefix="/api/activities")

VALID_ACTIVITY_CATEGORIES = [
    "Land preparation",
    "Sowing and planting",
    "Irrigation",
    "Fertilizer application",
    "Pesticide application",
    "Weed management",
    "Crop inspection",
    "Disease monitoring",
    "Harvesting",
    "Other activities"
]

CATEGORY_LOOKUP = {
    "land preparation": "Land preparation",
    "land prep": "Land preparation",
    "tillage": "Land preparation",
    "plowing": "Land preparation",
    "sowing and planting": "Sowing and planting",
    "sowing": "Sowing and planting",
    "planting": "Sowing and planting",
    "irrigation": "Irrigation",
    "watering": "Irrigation",
    "fertilizer application": "Fertilizer application",
    "fertilizer": "Fertilizer application",
    "fertilizers": "Fertilizer application",
    "manure": "Fertilizer application",
    "pesticide application": "Pesticide application",
    "pesticide": "Pesticide application",
    "pesticides": "Pesticide application",
    "spraying": "Pesticide application",
    "weed management": "Weed management",
    "weeding": "Weed management",
    "weed control": "Weed management",
    "crop inspection": "Crop inspection",
    "inspection": "Crop inspection",
    "field check": "Crop inspection",
    "disease monitoring": "Disease monitoring",
    "disease check": "Disease monitoring",
    "pest monitoring": "Disease monitoring",
    "harvesting": "Harvesting",
    "harvest": "Harvesting",
    "other activities": "Other activities",
    "other": "Other activities",
    "general": "Other activities"
}

VALID_PRIORITIES = ["Low", "Medium", "High"]
VALID_STATUSES = ["Pending", "In Progress", "Completed", "Postponed"]


def _authenticate():
    """Extract and validate user ID from Bearer token."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, (jsonify({
            "status": "error",
            "message": "Authentication required. Please log in."
        }), 401)

    token = auth_header.split(" ", 1)[1].strip()
    user_id = get_user_id_from_token(token)
    if not user_id:
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


def _insert_notification_if_new(connection, cursor, user_id, category, title, message, severity="info", link=None, unique_key=None, related_id=None):
    """Safely insert a notification avoiding duplicates via unique_key."""
    if unique_key:
        cursor.execute("""
            SELECT id FROM notifications
            WHERE user_id = %s AND unique_key = %s
        """, (user_id, unique_key))
        if cursor.fetchone():
            return False

    cursor.execute("""
        INSERT INTO notifications (user_id, category, title, message, severity, link, unique_key, related_id, is_read, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, NOW())
    """, (user_id, category, title, message, severity, link, unique_key, related_id))
    return True


def sync_activity_notifications_for_user(user_id, cursor, connection):
    """
    Sync upcoming, overdue, and high-priority activity alerts into the notifications table.
    Respects user notification preferences and individual activity reminder toggle.
    """
    try:
        # Check preference
        cursor.execute("""
            SELECT activity_reminders FROM notification_preferences
            WHERE user_id = %s
        """, (user_id,))
        pref = cursor.fetchone()
        if pref and not pref.get("activity_reminders", 1):
            return 0

        today = date.today()
        today_str = today.strftime("%Y-%m-%d")
        tomorrow = today + timedelta(days=1)
        tomorrow_str = tomorrow.strftime("%Y-%m-%d")

        cursor.execute("""
            SELECT a.id, a.title, a.category, a.priority, a.status, a.scheduled_date, a.scheduled_time,
                   c.crop_name, f.farm_name
            FROM farm_activities a
            LEFT JOIN crops c ON a.crop_id = c.id
            LEFT JOIN farms f ON a.farm_id = f.id
            WHERE a.user_id = %s AND a.reminder_enabled = 1 AND a.status IN ('Pending', 'In Progress')
        """, (user_id,))
        activities = cursor.fetchall()

        inserted_count = 0
        for act in activities:
            act_id = act["id"]
            title = act["title"]
            sched_date = act["scheduled_date"]
            if isinstance(sched_date, datetime):
                sched_date = sched_date.date()
            priority = act["priority"]
            crop_name = act.get("crop_name") or ""
            crop_suffix = f" for {crop_name}" if crop_name else ""

            # 1. Activity Scheduled Today
            if sched_date == today:
                u_key = f"act_today_{act_id}_{today_str}"
                severity = "urgent" if priority == "High" else "info"
                time_str = f" at {_format_time(act.get('scheduled_time'))}" if act.get('scheduled_time') else ""
                msg = f"Task '{title}'{crop_suffix} is scheduled for today{time_str}. Priority: {priority}."
                if _insert_notification_if_new(connection, cursor, user_id, "crop", f"Activity Due Today: {title}", msg, severity, "#activitySection", u_key, act_id):
                    inserted_count += 1

            # 2. Activity Overdue
            elif sched_date < today:
                days_overdue = (today - sched_date).days
                u_key = f"act_overdue_{act_id}_{today_str}"
                severity = "urgent" if priority == "High" else "warning"
                msg = f"Task '{title}'{crop_suffix} was scheduled for {sched_date.strftime('%Y-%m-%d')} ({days_overdue} days overdue)."
                if _insert_notification_if_new(connection, cursor, user_id, "crop", f"Overdue Farm Task: {title}", msg, severity, "#activitySection", u_key, act_id):
                    inserted_count += 1

            # 3. High Priority Scheduled Tomorrow
            elif sched_date == tomorrow and priority == "High":
                u_key = f"act_high_tomorrow_{act_id}_{tomorrow_str}"
                msg = f"High priority task '{title}'{crop_suffix} is scheduled for tomorrow ({tomorrow_str})."
                if _insert_notification_if_new(connection, cursor, user_id, "crop", f"Upcoming High Priority Task: {title}", msg, "warning", "#activitySection", u_key, act_id):
                    inserted_count += 1

        return inserted_count
    except Exception as e:
        print(f"Error syncing activity notifications: {e}")
        return 0


# =========================================================
# ENDPOINTS
# =========================================================

@activity_bp.route("/summary", methods=["GET"])
def get_activity_summary():
    """
    Get activity metrics: today's count, upcoming, overdue, completed, pending, category breakdown,
    plus lists of today's activities and upcoming activities.
    """
    user_id, err = _authenticate()
    if err:
        return err

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        today = date.today()
        today_str = today.strftime("%Y-%m-%d")
        next_week = today + timedelta(days=7)
        next_week_str = next_week.strftime("%Y-%m-%d")

        # Sync notifications in background
        sync_activity_notifications_for_user(user_id, cursor, conn)
        conn.commit()

        # 1. Total counts by status and timeframe
        cursor.execute("""
            SELECT 
                COUNT(*) AS total_count,
                SUM(CASE WHEN scheduled_date = %s AND status IN ('Pending', 'In Progress') THEN 1 ELSE 0 END) AS today_count,
                SUM(CASE WHEN scheduled_date > %s AND scheduled_date <= %s AND status IN ('Pending', 'In Progress') THEN 1 ELSE 0 END) AS upcoming_count,
                SUM(CASE WHEN scheduled_date < %s AND status IN ('Pending', 'In Progress') THEN 1 ELSE 0 END) AS overdue_count,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed_count,
                SUM(CASE WHEN status IN ('Pending', 'In Progress') THEN 1 ELSE 0 END) AS pending_count
            FROM farm_activities
            WHERE user_id = %s
        """, (today_str, today_str, next_week_str, today_str, user_id))
        counts = cursor.fetchone() or {}

        # 2. Category Breakdown
        cursor.execute("""
            SELECT category, COUNT(*) AS count
            FROM farm_activities
            WHERE user_id = %s
            GROUP BY category
            ORDER BY count DESC
        """, (user_id,))
        by_category = {r["category"]: r["count"] for r in cursor.fetchall()}

        # 3. Priority Breakdown
        cursor.execute("""
            SELECT priority, COUNT(*) AS count
            FROM farm_activities
            WHERE user_id = %s
            GROUP BY priority
        """, (user_id,))
        by_priority = {r["priority"]: r["count"] for r in cursor.fetchall()}

        # 4. Today's Activities
        cursor.execute("""
            SELECT a.*, c.crop_name, f.farm_name
            FROM farm_activities a
            LEFT JOIN crops c ON a.crop_id = c.id
            LEFT JOIN farms f ON a.farm_id = f.id
            WHERE a.user_id = %s AND a.scheduled_date = %s
            ORDER BY a.priority = 'High' DESC, a.priority = 'Medium' DESC, a.scheduled_time ASC, a.id DESC
        """, (user_id, today_str))
        today_acts = cursor.fetchall()
        for a in today_acts:
            a["scheduled_date"] = _format_date(a["scheduled_date"])
            a["scheduled_time"] = _format_time(a.get("scheduled_time"))
            a["completion_date"] = _format_date(a.get("completion_date"))

        # 5. Upcoming Activities (Next 7 days excluding today)
        cursor.execute("""
            SELECT a.*, c.crop_name, f.farm_name
            FROM farm_activities a
            LEFT JOIN crops c ON a.crop_id = c.id
            LEFT JOIN farms f ON a.farm_id = f.id
            WHERE a.user_id = %s AND a.scheduled_date > %s AND a.scheduled_date <= %s
              AND a.status IN ('Pending', 'In Progress')
            ORDER BY a.scheduled_date ASC, a.priority = 'High' DESC, a.scheduled_time ASC
            LIMIT 10
        """, (user_id, today_str, next_week_str))
        upcoming_acts = cursor.fetchall()
        for a in upcoming_acts:
            a["scheduled_date"] = _format_date(a["scheduled_date"])
            a["scheduled_time"] = _format_time(a.get("scheduled_time"))
            a["completion_date"] = _format_date(a.get("completion_date"))

        # 6. Overdue Activities
        cursor.execute("""
            SELECT a.*, c.crop_name, f.farm_name
            FROM farm_activities a
            LEFT JOIN crops c ON a.crop_id = c.id
            LEFT JOIN farms f ON a.farm_id = f.id
            WHERE a.user_id = %s AND a.scheduled_date < %s
              AND a.status IN ('Pending', 'In Progress')
            ORDER BY a.scheduled_date ASC, a.priority = 'High' DESC
            LIMIT 10
        """, (user_id, today_str))
        overdue_acts = cursor.fetchall()
        for a in overdue_acts:
            a["scheduled_date"] = _format_date(a["scheduled_date"])
            a["scheduled_time"] = _format_time(a.get("scheduled_time"))
            a["completion_date"] = _format_date(a.get("completion_date"))

        return jsonify({
            "status": "success",
            "summary": {
                "today_count": int(counts.get("today_count") or 0),
                "upcoming_count": int(counts.get("upcoming_count") or 0),
                "overdue_count": int(counts.get("overdue_count") or 0),
                "completed_count": int(counts.get("completed_count") or 0),
                "pending_count": int(counts.get("pending_count") or 0),
                "total_count": int(counts.get("total_count") or 0),
                "by_category": by_category,
                "by_priority": by_priority,
                "today_activities": today_acts,
                "upcoming_activities": upcoming_acts,
                "overdue_activities": overdue_acts
            }
        }), 200

    except Exception as e:
        print(f"Error fetching activity summary: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to fetch activity summary."
        }), 500
    finally:
        if conn:
            conn.close()


@activity_bp.route("", methods=["GET"])
def list_activities():
    """
    List farm activities with optional filtering by status, category, crop_id, priority, and date range.
    """
    user_id, err = _authenticate()
    if err:
        return err

    status_filter = request.args.get("status", "all").strip()
    category_filter = request.args.get("category", "all").strip()
    crop_filter = request.args.get("crop_id", "all").strip()
    priority_filter = request.args.get("priority", "all").strip()
    from_date = request.args.get("from_date", "").strip()
    to_date = request.args.get("to_date", "").strip()
    limit = min(int(request.args.get("limit", 100)), 300)
    offset = max(int(request.args.get("offset", 0)), 0)

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT a.*, c.crop_name, c.variety, f.farm_name, f.location AS farm_location
            FROM farm_activities a
            LEFT JOIN crops c ON a.crop_id = c.id
            LEFT JOIN farms f ON a.farm_id = f.id
            WHERE a.user_id = %s
        """
        params = [user_id]

        if status_filter and status_filter.lower() != "all":
            # Match status
            normalized_status = next((s for s in VALID_STATUSES if s.lower() == status_filter.lower()), status_filter)
            query += " AND a.status = %s"
            params.append(normalized_status)

        if category_filter and category_filter.lower() != "all":
            norm_cat = CATEGORY_LOOKUP.get(category_filter.lower(), category_filter)
            query += " AND a.category = %s"
            params.append(norm_cat)

        if crop_filter and crop_filter.lower() != "all" and crop_filter.isdigit():
            query += " AND a.crop_id = %s"
            params.append(int(crop_filter))

        if priority_filter and priority_filter.lower() != "all":
            norm_prio = next((p for p in VALID_PRIORITIES if p.lower() == priority_filter.lower()), priority_filter)
            query += " AND a.priority = %s"
            params.append(norm_prio)

        if from_date:
            query += " AND a.scheduled_date >= %s"
            params.append(from_date)

        if to_date:
            query += " AND a.scheduled_date <= %s"
            params.append(to_date)

        query += " ORDER BY a.scheduled_date ASC, a.scheduled_time ASC, a.priority = 'High' DESC, a.id DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        activities = []
        for r in rows:
            activities.append({
                "id": r["id"],
                "user_id": r["user_id"],
                "farm_id": r["farm_id"],
                "farm_name": r.get("farm_name"),
                "farm_location": r.get("farm_location"),
                "crop_id": r["crop_id"],
                "crop_name": r.get("crop_name"),
                "crop_variety": r.get("variety"),
                "title": r["title"],
                "description": r["description"] or "",
                "category": r["category"],
                "priority": r["priority"],
                "status": r["status"],
                "scheduled_date": _format_date(r["scheduled_date"]),
                "scheduled_time": _format_time(r.get("scheduled_time")),
                "reminder_enabled": bool(r.get("reminder_enabled", 1)),
                "completion_date": _format_date(r.get("completion_date")),
                "notes": r["notes"] or "",
                "created_at": r["created_at"].strftime("%Y-%m-%d %H:%M:%S") if r.get("created_at") else None
            })

        return jsonify({
            "status": "success",
            "activities": activities,
            "count": len(activities)
        }), 200

    except Exception as e:
        print(f"Error listing activities: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to list activities."
        }), 500
    finally:
        if conn:
            conn.close()


@activity_bp.route("/<int:activity_id>", methods=["GET"])
def get_activity_detail(activity_id):
    """Retrieve full details for a single activity."""
    user_id, err = _authenticate()
    if err:
        return err

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT a.*, c.crop_name, c.variety, f.farm_name, f.location AS farm_location
            FROM farm_activities a
            LEFT JOIN crops c ON a.crop_id = c.id
            LEFT JOIN farms f ON a.farm_id = f.id
            WHERE a.id = %s AND a.user_id = %s
        """, (activity_id, user_id))
        r = cursor.fetchone()

        if not r:
            return jsonify({
                "status": "error",
                "message": "Activity not found."
            }), 404

        activity = {
            "id": r["id"],
            "user_id": r["user_id"],
            "farm_id": r["farm_id"],
            "farm_name": r.get("farm_name"),
            "farm_location": r.get("farm_location"),
            "crop_id": r["crop_id"],
            "crop_name": r.get("crop_name"),
            "crop_variety": r.get("variety"),
            "title": r["title"],
            "description": r["description"] or "",
            "category": r["category"],
            "priority": r["priority"],
            "status": r["status"],
            "scheduled_date": _format_date(r["scheduled_date"]),
            "scheduled_time": _format_time(r.get("scheduled_time")),
            "reminder_enabled": bool(r.get("reminder_enabled", 1)),
            "completion_date": _format_date(r.get("completion_date")),
            "notes": r["notes"] or "",
            "created_at": r["created_at"].strftime("%Y-%m-%d %H:%M:%S") if r.get("created_at") else None
        }

        return jsonify({
            "status": "success",
            "activity": activity
        }), 200

    except Exception as e:
        print(f"Error fetching activity detail: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to fetch activity."
        }), 500
    finally:
        if conn:
            conn.close()


@activity_bp.route("", methods=["POST"])
def create_activity():
    """Create a new farm activity record with validation."""
    user_id, err = _authenticate()
    if err:
        return err

    data = request.get_json(silent=True) or {}

    title = str(data.get("title", "")).strip()
    category = str(data.get("category", "")).strip()
    scheduled_date_raw = str(data.get("scheduled_date", "")).strip()
    scheduled_time_raw = data.get("scheduled_time")
    priority_raw = str(data.get("priority", "Medium")).strip()
    status_raw = str(data.get("status", "Pending")).strip()
    description = str(data.get("description", "")).strip() if data.get("description") else None
    notes = str(data.get("notes", "")).strip() if data.get("notes") else None
    farm_id = data.get("farm_id")
    crop_id = data.get("crop_id")
    reminder_enabled = 1 if data.get("reminder_enabled", True) else 0

    # 1. Title Validation
    if not title:
        return jsonify({
            "status": "error",
            "message": "Activity title is required."
        }), 400
    if len(title) > 200:
        return jsonify({
            "status": "error",
            "message": "Activity title must not exceed 200 characters."
        }), 400

    # 2. Category Validation
    normalized_cat = CATEGORY_LOOKUP.get(category.lower())
    if not normalized_cat:
        normalized_cat = next((c for c in VALID_ACTIVITY_CATEGORIES if c.lower() == category.lower()), None)
    if not normalized_cat:
        return jsonify({
            "status": "error",
            "message": f"Invalid category. Must be one of: {', '.join(VALID_ACTIVITY_CATEGORIES)}"
        }), 400

    # 3. Scheduled Date Validation
    if not scheduled_date_raw:
        return jsonify({
            "status": "error",
            "message": "Scheduled date is required."
        }), 400
    try:
        scheduled_date = datetime.strptime(scheduled_date_raw, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({
            "status": "error",
            "message": "Invalid date format. Expected YYYY-MM-DD."
        }), 400

    # 4. Optional Scheduled Time Validation
    scheduled_time = None
    if scheduled_time_raw:
        scheduled_time_str = str(scheduled_time_raw).strip()
        if scheduled_time_str:
            time_match = re.match(r"^([01]\d|2[0-3]):([0-5]\d)(:([0-5]\d))?$", scheduled_time_str)
            if not time_match:
                return jsonify({
                    "status": "error",
                    "message": "Invalid time format. Expected HH:MM."
                }), 400
            scheduled_time = scheduled_time_str[:5]

    # 5. Priority & Status
    priority = next((p for p in VALID_PRIORITIES if p.lower() == priority_raw.lower()), "Medium")
    status = next((s for s in VALID_STATUSES if s.lower() == status_raw.lower()), "Pending")
    completion_date = date.today() if status == "Completed" else None

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 6. Verify Farm ownership if provided
        validated_farm_id = None
        if farm_id is not None and str(farm_id).strip() != "":
            try:
                fid = int(farm_id)
                cursor.execute("SELECT id FROM farms WHERE id = %s AND user_id = %s", (fid, user_id))
                if cursor.fetchone():
                    validated_farm_id = fid
                else:
                    return jsonify({"status": "error", "message": "Selected farm was not found."}), 400
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid farm ID."}), 400

        # 7. Verify Crop ownership if provided
        validated_crop_id = None
        if crop_id is not None and str(crop_id).strip() != "":
            try:
                cid = int(crop_id)
                cursor.execute("SELECT id, farm_id FROM crops WHERE id = %s AND user_id = %s", (cid, user_id))
                c_row = cursor.fetchone()
                if c_row:
                    validated_crop_id = cid
                    if validated_farm_id is None and c_row.get("farm_id"):
                        validated_farm_id = c_row["farm_id"]
                else:
                    return jsonify({"status": "error", "message": "Selected crop was not found."}), 400
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid crop ID."}), 400

        cursor.execute("""
            INSERT INTO farm_activities (
                user_id, farm_id, crop_id, title, description, category, priority, status,
                scheduled_date, scheduled_time, reminder_enabled, completion_date, notes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id, validated_farm_id, validated_crop_id, title, description,
            normalized_cat, priority, status, scheduled_date, scheduled_time,
            reminder_enabled, completion_date, notes
        ))
        conn.commit()
        activity_id = cursor.lastrowid

        # Sync notifications if scheduled today/tomorrow
        sync_activity_notifications_for_user(user_id, cursor, conn)
        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Farm activity scheduled successfully.",
            "activity_id": activity_id
        }), 201

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error creating farm activity: {e}")
        return jsonify({
            "status": "error",
            "message": "Failed to create farm activity."
        }), 500
    finally:
        if conn:
            conn.close()


@activity_bp.route("/<int:activity_id>", methods=["PUT"])
def update_activity(activity_id):
    """Update an existing activity record with full validation."""
    user_id, err = _authenticate()
    if err:
        return err

    data = request.get_json(silent=True) or {}

    title = str(data.get("title", "")).strip()
    category = str(data.get("category", "")).strip()
    scheduled_date_raw = str(data.get("scheduled_date", "")).strip()
    scheduled_time_raw = data.get("scheduled_time")
    priority_raw = str(data.get("priority", "Medium")).strip()
    status_raw = str(data.get("status", "Pending")).strip()
    description = str(data.get("description", "")).strip() if data.get("description") else None
    notes = str(data.get("notes", "")).strip() if data.get("notes") else None
    farm_id = data.get("farm_id")
    crop_id = data.get("crop_id")
    reminder_enabled = 1 if data.get("reminder_enabled", True) else 0

    if not title:
        return jsonify({"status": "error", "message": "Activity title is required."}), 400
    if len(title) > 200:
        return jsonify({"status": "error", "message": "Activity title must not exceed 200 characters."}), 400

    normalized_cat = CATEGORY_LOOKUP.get(category.lower())
    if not normalized_cat:
        normalized_cat = next((c for c in VALID_ACTIVITY_CATEGORIES if c.lower() == category.lower()), None)
    if not normalized_cat:
        return jsonify({
            "status": "error",
            "message": f"Invalid category. Must be one of: {', '.join(VALID_ACTIVITY_CATEGORIES)}"
        }), 400

    try:
        scheduled_date = datetime.strptime(scheduled_date_raw, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid date format. Expected YYYY-MM-DD."}), 400

    scheduled_time = None
    if scheduled_time_raw:
        scheduled_time_str = str(scheduled_time_raw).strip()
        if scheduled_time_str:
            time_match = re.match(r"^([01]\d|2[0-3]):([0-5]\d)(:([0-5]\d))?$", scheduled_time_str)
            if not time_match:
                return jsonify({"status": "error", "message": "Invalid time format. Expected HH:MM."}), 400
            scheduled_time = scheduled_time_str[:5]

    priority = next((p for p in VALID_PRIORITIES if p.lower() == priority_raw.lower()), "Medium")
    status = next((s for s in VALID_STATUSES if s.lower() == status_raw.lower()), "Pending")

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, status, completion_date FROM farm_activities WHERE id = %s AND user_id = %s", (activity_id, user_id))
        existing = cursor.fetchone()
        if not existing:
            return jsonify({"status": "error", "message": "Activity not found."}), 404

        # Manage completion date
        if status == "Completed":
            completion_date = existing["completion_date"] or date.today()
        else:
            completion_date = None

        # Verify Farm
        validated_farm_id = None
        if farm_id is not None and str(farm_id).strip() != "":
            try:
                fid = int(farm_id)
                cursor.execute("SELECT id FROM farms WHERE id = %s AND user_id = %s", (fid, user_id))
                if cursor.fetchone():
                    validated_farm_id = fid
                else:
                    return jsonify({"status": "error", "message": "Selected farm was not found."}), 400
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid farm ID."}), 400

        # Verify Crop
        validated_crop_id = None
        if crop_id is not None and str(crop_id).strip() != "":
            try:
                cid = int(crop_id)
                cursor.execute("SELECT id, farm_id FROM crops WHERE id = %s AND user_id = %s", (cid, user_id))
                c_row = cursor.fetchone()
                if c_row:
                    validated_crop_id = cid
                    if validated_farm_id is None and c_row.get("farm_id"):
                        validated_farm_id = c_row["farm_id"]
                else:
                    return jsonify({"status": "error", "message": "Selected crop was not found."}), 400
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid crop ID."}), 400

        cursor.execute("""
            UPDATE farm_activities SET
                farm_id = %s,
                crop_id = %s,
                title = %s,
                description = %s,
                category = %s,
                priority = %s,
                status = %s,
                scheduled_date = %s,
                scheduled_time = %s,
                reminder_enabled = %s,
                completion_date = %s,
                notes = %s
            WHERE id = %s AND user_id = %s
        """, (
            validated_farm_id, validated_crop_id, title, description,
            normalized_cat, priority, status, scheduled_date, scheduled_time,
            reminder_enabled, completion_date, notes, activity_id, user_id
        ))
        conn.commit()

        sync_activity_notifications_for_user(user_id, cursor, conn)
        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Activity updated successfully."
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error updating activity: {e}")
        return jsonify({"status": "error", "message": "Failed to update activity."}), 500
    finally:
        if conn:
            conn.close()


@activity_bp.route("/<int:activity_id>/status", methods=["PATCH"])
def patch_activity_status(activity_id):
    """Quick update activity status (e.g. Completed, In Progress, Postponed, Pending)."""
    user_id, err = _authenticate()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    status_raw = str(data.get("status", "")).strip()
    status = next((s for s in VALID_STATUSES if s.lower() == status_raw.lower()), None)
    if not status:
        return jsonify({
            "status": "error",
            "message": f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}"
        }), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM farm_activities WHERE id = %s AND user_id = %s", (activity_id, user_id))
        if not cursor.fetchone():
            return jsonify({"status": "error", "message": "Activity not found."}), 404

        completion_date = date.today() if status == "Completed" else None

        cursor.execute("""
            UPDATE farm_activities
            SET status = %s, completion_date = %s
            WHERE id = %s AND user_id = %s
        """, (status, completion_date, activity_id, user_id))
        conn.commit()

        return jsonify({
            "status": "success",
            "message": f"Activity status updated to '{status}'.",
            "status_value": status,
            "completion_date": _format_date(completion_date)
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error patching activity status: {e}")
        return jsonify({"status": "error", "message": "Failed to update status."}), 500
    finally:
        if conn:
            conn.close()


@activity_bp.route("/<int:activity_id>/postpone", methods=["PATCH"])
def postpone_activity(activity_id):
    """Postpone an activity to a new date."""
    user_id, err = _authenticate()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    new_date_raw = str(data.get("scheduled_date", "")).strip()
    notes = str(data.get("notes", "")).strip() if data.get("notes") else None

    if not new_date_raw:
        return jsonify({"status": "error", "message": "New scheduled date is required."}), 400
    try:
        new_date = datetime.strptime(new_date_raw, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid date format. Expected YYYY-MM-DD."}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, notes FROM farm_activities WHERE id = %s AND user_id = %s", (activity_id, user_id))
        act = cursor.fetchone()
        if not act:
            return jsonify({"status": "error", "message": "Activity not found."}), 404

        existing_notes = act.get("notes") or ""
        postpone_note = f"[Postponed to {new_date_raw}]" + (f" Reason: {notes}" if notes else "")
        updated_notes = f"{existing_notes}\n{postpone_note}".strip() if existing_notes else postpone_note

        cursor.execute("""
            UPDATE farm_activities
            SET scheduled_date = %s, status = 'Postponed', notes = %s
            WHERE id = %s AND user_id = %s
        """, (new_date, updated_notes, activity_id, user_id))
        conn.commit()

        return jsonify({
            "status": "success",
            "message": f"Activity postponed to {new_date_raw}.",
            "scheduled_date": new_date_raw
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error postponing activity: {e}")
        return jsonify({"status": "error", "message": "Failed to postpone activity."}), 500
    finally:
        if conn:
            conn.close()


@activity_bp.route("/<int:activity_id>", methods=["DELETE"])
def delete_activity(activity_id):
    """Delete a farm activity record."""
    user_id, err = _authenticate()
    if err:
        return err

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id FROM farm_activities WHERE id = %s AND user_id = %s", (activity_id, user_id))
        if not cursor.fetchone():
            return jsonify({"status": "error", "message": "Activity not found."}), 404

        cursor.execute("DELETE FROM farm_activities WHERE id = %s AND user_id = %s", (activity_id, user_id))
        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Activity deleted successfully."
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error deleting activity: {e}")
        return jsonify({"status": "error", "message": "Failed to delete activity."}), 500
    finally:
        if conn:
            conn.close()


@activity_bp.route("/calendar", methods=["GET"])
def get_calendar_activities():
    """
    Get activities grouped for a specific year and month.
    Query params: `year` (int, default current year), `month` (1-12, default current month),
    plus optional category and status filters.
    """
    user_id, err = _authenticate()
    if err:
        return err

    today = date.today()
    try:
        year = int(request.args.get("year", today.year))
        month = int(request.args.get("month", today.month))
        if month < 1 or month > 12:
            month = today.month
    except (ValueError, TypeError):
        year = today.year
        month = today.month

    category_filter = request.args.get("category", "all").strip()
    status_filter = request.args.get("status", "all").strip()

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get first day of month and days in month
        num_days = calendar.monthrange(year, month)[1]
        start_date = date(year, month, 1)
        end_date = date(year, month, num_days)

        query = """
            SELECT a.*, c.crop_name, f.farm_name
            FROM farm_activities a
            LEFT JOIN crops c ON a.crop_id = c.id
            LEFT JOIN farms f ON a.farm_id = f.id
            WHERE a.user_id = %s AND a.scheduled_date >= %s AND a.scheduled_date <= %s
        """
        params = [user_id, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")]

        if category_filter and category_filter.lower() != "all":
            norm_cat = CATEGORY_LOOKUP.get(category_filter.lower(), category_filter)
            query += " AND a.category = %s"
            params.append(norm_cat)

        if status_filter and status_filter.lower() != "all":
            norm_status = next((s for s in VALID_STATUSES if s.lower() == status_filter.lower()), status_filter)
            query += " AND a.status = %s"
            params.append(norm_status)

        query += " ORDER BY a.scheduled_date ASC, a.scheduled_time ASC, a.priority = 'High' DESC"

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        # Group activities by day string (e.g. "2026-11-15")
        days_map = {}
        for r in rows:
            d_str = _format_date(r["scheduled_date"])
            if d_str not in days_map:
                days_map[d_str] = []
            days_map[d_str].append({
                "id": r["id"],
                "title": r["title"],
                "category": r["category"],
                "priority": r["priority"],
                "status": r["status"],
                "scheduled_date": d_str,
                "scheduled_time": _format_time(r.get("scheduled_time")),
                "crop_name": r.get("crop_name"),
                "farm_name": r.get("farm_name")
            })

        # Build full month day structure
        days_list = []
        for d in range(1, num_days + 1):
            cur_d = date(year, month, d)
            cur_d_str = cur_d.strftime("%Y-%m-%d")
            acts = days_map.get(cur_d_str, [])
            days_list.append({
                "day": d,
                "date": cur_d_str,
                "weekday": cur_d.weekday(),  # 0=Monday, 6=Sunday
                "is_today": (cur_d == today),
                "activity_count": len(acts),
                "has_high_priority": any(a["priority"] == "High" for a in acts),
                "has_pending": any(a["status"] in ("Pending", "In Progress") for a in acts),
                "activities": acts
            })

        return jsonify({
            "status": "success",
            "year": year,
            "month": month,
            "month_name": calendar.month_name[month],
            "total_activities": len(rows),
            "days": days_list
        }), 200

    except Exception as e:
        print(f"Error fetching calendar activities: {e}")
        return jsonify({"status": "error", "message": "Failed to fetch calendar."}), 500
    finally:
        if conn:
            conn.close()


@activity_bp.route("/suggestions", methods=["GET"])
def get_activity_suggestions():
    """
    Generate crop-aware, disease-aware, and irrigation-aware activity suggestions.
    Crucially:
    - Labeled clearly as suggestions / recommendations.
    - Never marked completed automatically.
    - Never automatically schedule chemical treatments without farmer confirmation.
    """
    user_id, err = _authenticate()
    if err:
        return err

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        today = date.today()
        suggestions = []

        # 1. Inspect user crops and their growth stages
        cursor.execute("""
            SELECT c.id, c.crop_name, c.variety, c.planting_date, c.expected_harvest_date,
                   c.growth_status, f.id AS farm_id, f.farm_name
            FROM crops c
            LEFT JOIN farms f ON c.farm_id = f.id
            WHERE c.user_id = %s
            ORDER BY c.planting_date DESC
        """, (user_id,))
        crops = cursor.fetchall()

        for crop in crops:
            cid = crop["id"]
            cname = crop["crop_name"]
            stage = (crop.get("growth_status") or "").strip()
            p_date = crop.get("planting_date")
            h_date = crop.get("expected_harvest_date")
            fid = crop.get("farm_id")
            fname = crop.get("farm_name")

            # Days since planting
            days_since = None
            if p_date:
                if isinstance(p_date, datetime):
                    p_date = p_date.date()
                days_since = (today - p_date).days

            # Suggestions by growth stage
            stage_lower = stage.lower()
            if "newly planted" in stage_lower or (days_since is not None and days_since <= 7):
                suggestions.append({
                    "suggestion_id": f"sug_new_{cid}",
                    "title": f"Initial Soil Moisture & Germination Check: {cname}",
                    "description": f"Inspect seed germination emergence and verify moisture level for newly planted {cname}.",
                    "category": "Crop inspection",
                    "priority": "Medium",
                    "suggested_date": today.strftime("%Y-%m-%d"),
                    "crop_id": cid,
                    "crop_name": cname,
                    "farm_id": fid,
                    "farm_name": fname,
                    "reason": f"Crop was newly planted on {_format_date(p_date)}."
                })

            elif "flowering" in stage_lower:
                suggestions.append({
                    "suggestion_id": f"sug_flowering_{cid}",
                    "title": f"Flowering Health & Pest Monitoring: {cname}",
                    "description": f"Inspect flower clusters for pest pressure and maintain adequate soil moisture.",
                    "category": "Crop inspection",
                    "priority": "High",
                    "suggested_date": today.strftime("%Y-%m-%d"),
                    "crop_id": cid,
                    "crop_name": cname,
                    "farm_id": fid,
                    "farm_name": fname,
                    "reason": f"Crop is currently in the critical flowering stage."
                })

            elif "fruiting" in stage_lower:
                suggestions.append({
                    "suggestion_id": f"sug_fruiting_{cid}",
                    "title": f"Fruit Development & Moisture Stability: {cname}",
                    "description": f"Check fruit enlargement, prevent water stress, and check for fruit rot or borer signs.",
                    "category": "Crop inspection",
                    "priority": "Medium",
                    "suggested_date": today.strftime("%Y-%m-%d"),
                    "crop_id": cid,
                    "crop_name": cname,
                    "farm_id": fid,
                    "farm_name": fname,
                    "reason": f"Crop is in the fruiting development stage."
                })

            elif "ready for harvest" in stage_lower:
                suggestions.append({
                    "suggestion_id": f"sug_ready_harv_{cid}",
                    "title": f"Harvest Preparation & Labor Scheduling: {cname}",
                    "description": f"Inspect crop maturity indicators, prepare harvesting tools, and organize clean storage bags.",
                    "category": "Harvesting",
                    "priority": "High",
                    "suggested_date": today.strftime("%Y-%m-%d"),
                    "crop_id": cid,
                    "crop_name": cname,
                    "farm_id": fid,
                    "farm_name": fname,
                    "reason": f"Crop status is marked 'Ready for Harvest'."
                })

            elif "growing" in stage_lower:
                suggestions.append({
                    "suggestion_id": f"sug_growing_{cid}",
                    "title": f"Weed Control & Foliar Assessment: {cname}",
                    "description": f"Clear early competitive weeds and review crop leaf canopy development.",
                    "category": "Weed management",
                    "priority": "Medium",
                    "suggested_date": (today + timedelta(days=1)).strftime("%Y-%m-%d"),
                    "crop_id": cid,
                    "crop_name": cname,
                    "farm_id": fid,
                    "farm_name": fname,
                    "reason": f"Active vegetative growth phase."
                })

            # Check expected harvest date approaching
            if h_date:
                if isinstance(h_date, datetime):
                    h_date = h_date.date()
                diff_harvest = (h_date - today).days
                if 0 <= diff_harvest <= 7:
                    suggestions.append({
                        "suggestion_id": f"sug_harvest_date_{cid}",
                        "title": f"Plan Crop Harvest: {cname}",
                        "description": f"Expected harvest date is approaching on {h_date.strftime('%Y-%m-%d')}. Check mandi rates and prepare storage.",
                        "category": "Harvesting",
                        "priority": "High",
                        "suggested_date": h_date.strftime("%Y-%m-%d"),
                        "crop_id": cid,
                        "crop_name": cname,
                        "farm_id": fid,
                        "farm_name": fname,
                        "reason": f"Expected harvest is within {diff_harvest} days."
                    })

        # 2. Inspect recent disease diagnosis records
        cursor.execute("""
            SELECT d.id, d.predicted_class, d.confidence, d.diagnosis_date, c.crop_name
            FROM diagnosis_history d
            LEFT JOIN crops c ON d.crop_id = c.id
            WHERE d.user_id = %s AND d.diagnosis_date >= DATE_SUB(NOW(), INTERVAL 14 DAY)
            ORDER BY d.diagnosis_date DESC
            LIMIT 3
        """, (user_id,))
        diagnoses = cursor.fetchall()

        for diag in diagnoses:
            pred_class = diag["predicted_class"] or ""
            c_name = diag.get("crop_name") or (pred_class.split("___")[0].replace("_", " ") if "___" in pred_class else "Crop")
            d_name = pred_class.split("___")[1].replace("_", " ") if "___" in pred_class else pred_class
            diag_id = diag["id"]
            if d_name and "healthy" not in d_name.lower():
                suggestions.append({
                    "suggestion_id": f"sug_diag_{diag_id}",
                    "title": f"Follow-up Disease Monitoring: {d_name}",
                    "description": f"Conduct follow-up leaf inspection for {d_name} on {c_name} to verify treatment effectiveness.",
                    "category": "Disease monitoring",
                    "priority": "High",
                    "suggested_date": today.strftime("%Y-%m-%d"),
                    "crop_id": None,
                    "crop_name": c_name,
                    "farm_id": None,
                    "farm_name": None,
                    "reason": f"Recent scan detected '{d_name}' on {_format_date(diag['diagnosis_date'])}."
                })

        # 3. Inspect recent irrigation recommendation
        cursor.execute("""
            SELECT i.id, i.crop, i.recommendation_status, i.is_irrigation_needed, i.created_at
            FROM irrigation_history i
            WHERE i.user_id = %s AND i.created_at >= DATE_SUB(NOW(), INTERVAL 3 DAY)
            ORDER BY i.created_at DESC
            LIMIT 2
        """, (user_id,))
        irrigs = cursor.fetchall()

        for ir in irrigs:
            st = (ir.get("recommendation_status") or "").lower()
            c_name = ir.get("crop") or "Crop"
            ir_id = ir["id"]
            if st in ("urgent", "recommended") or ir.get("is_irrigation_needed") == 1:
                suggestions.append({
                    "suggestion_id": f"sug_irrig_{ir_id}",
                    "title": f"Scheduled Field Irrigation: {c_name}",
                    "description": f"Provide adequate irrigation based on recent advisory recommendations.",
                    "category": "Irrigation",
                    "priority": "High" if st == "urgent" else "Medium",
                    "suggested_date": today.strftime("%Y-%m-%d"),
                    "crop_id": None,
                    "crop_name": c_name,
                    "farm_id": None,
                    "farm_name": None,
                    "reason": f"Recent irrigation recommendation was '{st.capitalize() or 'Needed'}'."
                })

        # Limit to top 6 relevant suggestions
        return jsonify({
            "status": "success",
            "count": len(suggestions),
            "suggestions": suggestions[:6]
        }), 200

    except Exception as e:
        print(f"Error generating activity suggestions: {e}")
        return jsonify({"status": "error", "message": "Failed to generate suggestions."}), 500
    finally:
        if conn:
            conn.close()
