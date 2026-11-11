from datetime import date, datetime, timedelta
import os
import requests
from flask import Blueprint, jsonify, request
from config import get_db_connection
from utils.auth_tokens import get_user_id_from_token

notification_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")

WEATHER_API_BASE_URL = "https://api.weatherapi.com/v1"


def _authenticate():
    """Extract and validate user ID from Bearer token."""
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
            "message": "Invalid or expired login token. Please log in again."
        }), 401)

    return user_id, None


def _get_preferences(cursor, user_id):
    """Retrieve farmer's notification preferences, defaulting to enabled."""
    cursor.execute("""
        SELECT crop_reminders, irrigation_alerts, weather_alerts, disease_reminders, push_enabled, activity_reminders
        FROM notification_preferences
        WHERE user_id = %s
    """, (user_id,))
    row = cursor.fetchone()
    if row:
        return {
            "crop_reminders": bool(row.get("crop_reminders", 1)),
            "irrigation_alerts": bool(row.get("irrigation_alerts", 1)),
            "weather_alerts": bool(row.get("weather_alerts", 1)),
            "disease_reminders": bool(row.get("disease_reminders", 1)),
            "activity_reminders": bool(row.get("activity_reminders", 1)),
            "push_enabled": bool(row["push_enabled"]) if "push_enabled" in row and row["push_enabled"] is not None else True
        }
    return {
        "crop_reminders": True,
        "irrigation_alerts": True,
        "weather_alerts": True,
        "disease_reminders": True,
        "activity_reminders": True,
        "push_enabled": True
    }


def _insert_notification_if_new(connection, cursor, user_id, category, title, message, severity="info", link=None, unique_key=None, related_id=None):
    """Insert notification only if unique_key does not already exist for this user."""
    if unique_key:
        cursor.execute("""
            SELECT id FROM notifications
            WHERE user_id = %s AND unique_key = %s
        """, (user_id, unique_key))
        if cursor.fetchone():
            return False  # Already exists, skip duplicate

    cursor.execute("""
        INSERT INTO notifications (user_id, category, title, message, severity, link, unique_key, related_id, is_read, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, CURRENT_TIMESTAMP)
    """, (user_id, category, title, message, severity, link, unique_key, related_id))
    connection.commit()
    return True


def _generate_notifications(connection, cursor, user_id):
    """Generate reminders and alerts from real crops, irrigation, weather, and diagnosis records."""
    prefs = _get_preferences(cursor, user_id)
    today = date.today()

    # =========================================================================
    # 1. CROP REMINDERS
    # =========================================================================
    if prefs["crop_reminders"]:
        cursor.execute("""
            SELECT c.id, c.crop_name, c.variety, c.planting_date, c.expected_harvest_date,
                   c.growth_status, c.updated_at, f.farm_name
            FROM crops c
            LEFT JOIN farms f ON f.id = c.farm_id
            WHERE c.user_id = %s
        """, (user_id,))
        crops = cursor.fetchall() or []

        for crop in crops:
            crop_id = crop["id"]
            crop_name = crop.get("crop_name") or "Crop"
            variety = crop.get("variety")
            farm_name = crop.get("farm_name") or "Farm"
            harvest_date = crop.get("expected_harvest_date")
            growth_status = crop.get("growth_status") or "Newly Planted"
            updated_at = crop.get("updated_at")

            # A. Harvest date approaching (within 7 days)
            if harvest_date:
                h_date = harvest_date if isinstance(harvest_date, date) else datetime.strptime(str(harvest_date)[:10], "%Y-%m-%d").date()
                days_until_harvest = (h_date - today).days

                if 0 <= days_until_harvest <= 7 and growth_status != "Harvested":
                    unique_key = f"crop_harvest_approaching_{crop_id}_{h_date}"
                    title = f"Harvest Approaching: {crop_name}"
                    msg = f"{crop_name} ({variety or 'General'}) at {farm_name} is approaching its expected harvest date on {h_date} (in {days_until_harvest} days)."
                    _insert_notification_if_new(connection, cursor, user_id, "crop", title, msg, "info", "#farmCropSection", unique_key, related_id=crop_id)

                # B. Harvest date reached or passed
                elif days_until_harvest < 0 and growth_status != "Harvested":
                    unique_key = f"crop_harvest_reached_{crop_id}_{h_date}"
                    title = f"Harvest Ready: {crop_name}"
                    msg = f"{crop_name} at {farm_name} reached its expected harvest date on {h_date}. Please check readiness and update growth status."
                    _insert_notification_if_new(connection, cursor, user_id, "crop", title, msg, "warning", "#farmCropSection", unique_key, related_id=crop_id)

            # C. Crop unupdated for a long time (> 30 days)
            if updated_at and growth_status != "Harvested":
                u_date = updated_at.date() if isinstance(updated_at, datetime) else (updated_at if isinstance(updated_at, date) else None)
                if u_date and (today - u_date).days >= 30:
                    month_key = today.strftime("%Y-%m")
                    unique_key = f"crop_stale_{crop_id}_{month_key}"
                    title = f"Growth Update Needed: {crop_name}"
                    msg = f"No growth status update recorded for {crop_name} at {farm_name} in over 30 days. Updating status helps keep management advice accurate."
                    _insert_notification_if_new(connection, cursor, user_id, "crop", title, msg, "info", "#farmCropSection", unique_key, related_id=crop_id)

            # D. Growth stage care reminder
            st_lower = growth_status.lower()
            if "flower" in st_lower or "bloom" in st_lower:
                unique_key = f"crop_flowering_care_{crop_id}"
                title = f"Critical Stage: {crop_name} Flowering"
                msg = f"{crop_name} at {farm_name} is in the flowering phase. Maintain consistent soil moisture and avoid excessive moisture stress or harsh chemical sprays."
                _insert_notification_if_new(connection, cursor, user_id, "crop", title, msg, "info", "#farmCropSection", unique_key, related_id=crop_id)
            elif "fruit" in st_lower or "pod" in st_lower or "grain" in st_lower:
                unique_key = f"crop_fruiting_care_{crop_id}"
                title = f"Care Advisory: {crop_name} Fruiting"
                msg = f"{crop_name} at {farm_name} is fruiting. Monitor soil moisture regularly to prevent fruit cracking or premature fruit drop."
                _insert_notification_if_new(connection, cursor, user_id, "crop", title, msg, "info", "#farmCropSection", unique_key, related_id=crop_id)
            elif "seed" in st_lower or "plant" in st_lower or "sow" in st_lower:
                unique_key = f"crop_seedling_care_{crop_id}"
                title = f"Seedling Care: {crop_name}"
                msg = f"Tender {crop_name} seedlings at {farm_name} require light, frequent watering and crust prevention. Check germination progress."
                _insert_notification_if_new(connection, cursor, user_id, "crop", title, msg, "info", "#farmCropSection", unique_key, related_id=crop_id)

    # =========================================================================
    # 2. IRRIGATION ALERTS (Feature Upgrade 3 Integration)
    # =========================================================================
    if prefs["irrigation_alerts"]:
        cursor.execute("""
            SELECT id, crop, soil_moisture, is_irrigation_needed, water_quantity_mm,
                   recommendation_status, soil_type, growth_stage, water_saved_mm, created_at
            FROM irrigation_history
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 5
        """, (user_id,))
        irrig_records = cursor.fetchall() or []

        for rec in irrig_records:
            rec_id = rec["id"]
            crop_name = rec.get("crop") or "Crop"
            needed = bool(rec.get("is_irrigation_needed"))
            status = rec.get("recommendation_status") or "Recorded"
            moisture = rec.get("soil_moisture")
            water_mm = rec.get("water_quantity_mm")
            water_saved = float(rec.get("water_saved_mm") or 0.0)
            g_stage = rec.get("growth_stage")

            # A. Rain Postponement (Water Conserved)
            if "postpone" in status.lower() or water_saved > 0:
                unique_key = f"irrig_postpone_{rec_id}"
                title = f"Irrigation Postponed for Rain: {crop_name}"
                litres_str = f" ({int(water_saved * 10000):,} L/ha)" if water_saved > 0 else ""
                msg = f"Upcoming rainfall allows postponing irrigation for {crop_name}, conserving ~{water_saved:.1f} mm depth{litres_str}. Recheck moisture post-rainfall."
                _insert_notification_if_new(connection, cursor, user_id, "irrigation", title, msg, "info", "irrigation.html", unique_key, related_id=rec_id)

            # B. Urgent Moisture Deficit Alert
            elif status == "Urgent":
                unique_key = f"irrig_urgent_{rec_id}"
                title = f"Urgent Irrigation Needed: {crop_name}"
                moist_str = f"{moisture}%" if moisture is not None else "Deficit"
                msg = f"Critical soil moisture deficit detected for {crop_name} (Moisture: {moist_str}). Immediate replenishment of {water_mm} mm depth recommended."
                _insert_notification_if_new(connection, cursor, user_id, "irrigation", title, msg, "urgent", "irrigation.html", unique_key, related_id=rec_id)

            # C. Recommended Irrigation
            elif needed:
                unique_key = f"irrig_needed_{rec_id}"
                title = f"Irrigation Required: {crop_name}"
                moist_str = f"{moisture}%" if moisture is not None else "Deficit"
                msg = f"Assessment for {crop_name} indicated moisture deficit ({moist_str}). Recommended water application: {water_mm} mm."
                _insert_notification_if_new(connection, cursor, user_id, "irrigation", title, msg, "warning", "irrigation.html", unique_key, related_id=rec_id)

            # D. Qualitative Unmeasured Guidance Check
            elif "guidance" in status.lower() or "unmeasured" in status.lower():
                unique_key = f"irrig_unmeasured_{rec_id}"
                title = f"Soil Moisture Tactile Check: {crop_name}"
                msg = f"Unmeasured guidance recorded for {crop_name}. Perform a 15–20 cm root-zone tactile squeeze check before operating irrigation equipment."
                _insert_notification_if_new(connection, cursor, user_id, "irrigation", title, msg, "info", "irrigation.html", unique_key, related_id=rec_id)

            # E. Satisfactory check recorded
            else:
                unique_key = f"irrig_logged_{rec_id}"
                title = f"Irrigation Check Recorded: {crop_name}"
                moist_str = f"{moisture}%" if moisture is not None else "Satisfactory"
                msg = f"Guidance '{status}' recorded for {crop_name} (Soil Moisture: {moist_str}). Field conditions were satisfactory."
                _insert_notification_if_new(connection, cursor, user_id, "irrigation", title, msg, "info", "irrigation.html", unique_key, related_id=rec_id)

    # =========================================================================
    # 3. WEATHER ALERTS (WeatherAPI Live Integration)
    # =========================================================================
    if prefs["weather_alerts"]:
        cursor.execute("""
            SELECT location FROM farms WHERE user_id = %s AND location IS NOT NULL AND location != '' LIMIT 1
        """, (user_id,))
        farm_loc_row = cursor.fetchone()
        farm_loc = farm_loc_row["location"] if farm_loc_row else None

        if not farm_loc:
            cursor.execute("""
                SELECT location FROM irrigation_history WHERE user_id = %s AND location IS NOT NULL AND location != '' LIMIT 1
            """, (user_id,))
            irrig_loc_row = cursor.fetchone()
            farm_loc = irrig_loc_row["location"] if irrig_loc_row else None

        weather_key = os.getenv("WEATHER_API_KEY", "").strip()

        if farm_loc and weather_key:
            clean_city = farm_loc.split(",")[0].strip()
            try:
                url = f"{WEATHER_API_BASE_URL}/forecast.json"
                params = {"key": weather_key, "q": clean_city, "days": 2, "aqi": "no", "alerts": "yes"}
                resp = requests.get(url, params=params, timeout=4)
                if resp.ok:
                    wdata = resp.json()
                    forecast_days = wdata.get("forecast", {}).get("forecastday", [])
                    for fday in forecast_days:
                        f_date = fday.get("date")
                        day_info = fday.get("day", {})
                        max_temp = day_info.get("maxtemp_c")
                        precip_mm = day_info.get("totalprecip_mm")
                        chance_rain = day_info.get("daily_chance_of_rain")
                        max_wind = day_info.get("maxwind_kph")

                        # A. Heavy rainfall advisory
                        if (precip_mm is not None and precip_mm >= 25.0) or (chance_rain is not None and chance_rain >= 80):
                            unique_key = f"weather_rain_{clean_city}_{f_date}"
                            title = f"Heavy Rain Advisory: {clean_city}"
                            msg = f"Heavy rainfall forecast for {clean_city} on {f_date} (Rain chance: {chance_rain}%, {precip_mm} mm). Postpone irrigation and inspect farm drainage."
                            _insert_notification_if_new(connection, cursor, user_id, "weather", title, msg, "warning", "weather.html", unique_key)

                        # B. High temperature warning
                        if max_temp is not None and max_temp >= 38.0:
                            unique_key = f"weather_heat_{clean_city}_{f_date}"
                            title = f"High Temperature Warning: {clean_city}"
                            msg = f"High temperature expected in {clean_city} on {f_date} (Max: {max_temp}°C). Provide shade for nursery beds and avoid midday irrigation."
                            _insert_notification_if_new(connection, cursor, user_id, "weather", title, msg, "warning", "weather.html", unique_key)

                        # C. Strong wind warning
                        if max_wind is not None and max_wind >= 35.0:
                            unique_key = f"weather_wind_{clean_city}_{f_date}"
                            title = f"Strong Wind Advisory: {clean_city}"
                            msg = f"High wind speeds forecast for {clean_city} on {f_date} (Max wind: {max_wind} km/h). Stake vulnerable tall crops and delay chemical spray applications."
                            _insert_notification_if_new(connection, cursor, user_id, "weather", title, msg, "warning", "weather.html", unique_key)

                        # D. High evaporation / irrigation review advisory
                        if max_temp is not None and max_temp >= 34.0 and (precip_mm is None or precip_mm < 2.0):
                            unique_key = f"weather_evap_{clean_city}_{f_date}"
                            title = f"High Evaporation Alert: {clean_city}"
                            msg = f"Dry, hot conditions expected in {clean_city} on {f_date} (Max: {max_temp}°C). Review root-zone soil moisture and schedule irrigation during cooler hours."
                            _insert_notification_if_new(connection, cursor, user_id, "weather", title, msg, "info", "irrigation.html", unique_key)
            except Exception as e:
                # Silently catch network timeouts; do NOT invent weather alerts
                pass

    # =========================================================================
    # 4. DISEASE PREVENTION & DIAGNOSIS ALERTS
    # =========================================================================
    if prefs["disease_reminders"]:
        cursor.execute("""
            SELECT dh.id, dh.predicted_class, dh.confidence, dh.diagnosis_date
            FROM diagnosis_history dh
            WHERE dh.user_id = %s
            ORDER BY dh.diagnosis_date DESC
            LIMIT 5
        """, (user_id,))
        diags = cursor.fetchall() or []

        for d in diags:
            pred_cls = d.get("predicted_class") or ""
            diag_id = d["id"]
            conf = d.get("confidence")
            conf_str = f" ({conf:.1f}% confidence)" if conf is not None else ""

            if "___" in pred_cls:
                crop_part, disease_part = pred_cls.split("___", 1)
                crop_name = crop_part.replace("_", " ").title()
                disease_name = disease_part.replace("_", " ").title()

                if "healthy" not in disease_part.lower():
                    unique_key = f"disease_followup_{diag_id}"
                    title = f"Disease Prevention: {disease_name}"
                    msg = f"Previous check found {disease_name} on {crop_name}{conf_str}. Ensure field sanitation, prune infected foliage, and avoid overhead watering to prevent spore spread."
                    _insert_notification_if_new(connection, cursor, user_id, "disease", title, msg, "warning", "disease.html#diagnosisHistorySection", unique_key, related_id=diag_id)
                else:
                    unique_key = f"disease_healthy_{diag_id}"
                    title = f"Crop Health Confirmed: {crop_name}"
                    msg = f"Recent diagnosis confirmed healthy foliage for {crop_name}{conf_str}. Continue preventive sanitation and routine field scouting."
                    _insert_notification_if_new(connection, cursor, user_id, "disease", title, msg, "info", "disease.html#diagnosisHistorySection", unique_key, related_id=diag_id)

        # General seasonal reminder if registered crops exist
        cursor.execute("SELECT DISTINCT crop_name FROM crops WHERE user_id = %s LIMIT 3", (user_id,))
        farmer_crops = [r["crop_name"] for r in (cursor.fetchall() or []) if r.get("crop_name")]
        if farmer_crops:
            crop_list_str = ", ".join(farmer_crops)
            month_key = today.strftime("%Y-%m")
            unique_key = f"disease_general_inspection_{month_key}"
            title = "Routine Crop Health Inspection"
            msg = f"Inspect the undersides of leaves and stems on your registered {crop_list_str} for early signs of leaf spots, rusts, or pest activity."
            _insert_notification_if_new(connection, cursor, user_id, "disease", title, msg, "info", "disease.html", unique_key)

    # 5. Smart Farm Activities & Task Planner Reminders
    try:
        from routes.activity_routes import sync_activity_notifications_for_user
        sync_activity_notifications_for_user(user_id, cursor, connection)
    except Exception as e:
        print(f"Error invoking activity notifications sync: {e}")


# =============================================================================
# API ROUTES
# =============================================================================

@notification_bp.route("", methods=["GET"])
def get_notifications():
    """Retrieve notifications for authenticated farmer with optional filters."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Auto-generate any new pending notifications
        _generate_notifications(connection, cursor, user_id)

        unread_only = request.args.get("unread_only", "").lower() in ("true", "1")
        read_status = request.args.get("read_status", "").strip().lower()
        category = request.args.get("category", "").strip().lower()
        limit_param = request.args.get("limit", "50")

        try:
            limit = min(max(int(limit_param), 1), 100)
        except ValueError:
            limit = 50

        where_clauses = ["user_id = %s"]
        params = [user_id]

        if unread_only or read_status == "unread":
            where_clauses.append("is_read = 0")
        elif read_status == "read":
            where_clauses.append("is_read = 1")

        if category and category != "all":
            where_clauses.append("category = %s")
            params.append(category)

        where_sql = " AND ".join(where_clauses)

        cursor.execute(f"""
            SELECT id, category, title, message, severity, is_read, link, related_id, created_at
            FROM notifications
            WHERE {where_sql}
            ORDER BY created_at DESC, id DESC
            LIMIT %s
        """, tuple(params + [limit]))
        rows = cursor.fetchall() or []

        cursor.execute("SELECT COUNT(*) AS cnt FROM notifications WHERE user_id = %s AND is_read = 0", (user_id,))
        unread_count = int(cursor.fetchone()["cnt"] or 0)
        total_count = len(rows)

        formatted_notifications = []
        for r in rows:
            c_date = r.get("created_at")
            formatted_notifications.append({
                "id": r["id"],
                "category": r["category"],
                "title": r["title"],
                "message": r["message"],
                "severity": r["severity"],
                "is_read": bool(r["is_read"]),
                "link": r.get("link"),
                "related_id": r.get("related_id"),
                "created_at": c_date.strftime("%Y-%m-%d %H:%M:%S") if isinstance(c_date, (datetime, date)) else str(c_date)
            })

        return jsonify({
            "status": "success",
            "notifications": formatted_notifications,
            "unread_count": unread_count,
            "total_count": total_count
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Database error in notifications: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@notification_bp.route("/unread-count", methods=["GET"])
def get_unread_count():
    """Quick badge count of unread notifications."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) AS cnt FROM notifications WHERE user_id = %s AND is_read = 0", (user_id,))
        unread_count = int(cursor.fetchone()["cnt"] or 0)

        return jsonify({
            "status": "success",
            "unread_count": unread_count
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@notification_bp.route("/generate", methods=["POST"])
def trigger_generation():
    """Explicitly trigger notification generation for the farmer."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        _generate_notifications(connection, cursor, user_id)

        cursor.execute("SELECT COUNT(*) AS cnt FROM notifications WHERE user_id = %s AND is_read = 0", (user_id,))
        unread_count = int(cursor.fetchone()["cnt"] or 0)

        return jsonify({
            "status": "success",
            "message": "Notifications generated successfully.",
            "unread_count": unread_count
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@notification_bp.route("/<int:notification_id>/read", methods=["PATCH"])
def mark_notification_read(notification_id):
    """Mark single notification as read."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT id FROM notifications WHERE id = %s AND user_id = %s", (notification_id, user_id))
        if not cursor.fetchone():
            return jsonify({"status": "error", "message": "Notification not found."}), 404

        cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = %s AND user_id = %s", (notification_id, user_id))
        connection.commit()

        cursor.execute("SELECT COUNT(*) AS cnt FROM notifications WHERE user_id = %s AND is_read = 0", (user_id,))
        unread_count = int(cursor.fetchone()["cnt"] or 0)

        return jsonify({
            "status": "success",
            "message": "Notification marked as read.",
            "unread_count": unread_count
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@notification_bp.route("/<int:notification_id>/unread", methods=["PATCH"])
def mark_notification_unread(notification_id):
    """Mark single notification as unread."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT id FROM notifications WHERE id = %s AND user_id = %s", (notification_id, user_id))
        if not cursor.fetchone():
            return jsonify({"status": "error", "message": "Notification not found."}), 404

        cursor.execute("UPDATE notifications SET is_read = 0 WHERE id = %s AND user_id = %s", (notification_id, user_id))
        connection.commit()

        cursor.execute("SELECT COUNT(*) AS cnt FROM notifications WHERE user_id = %s AND is_read = 0", (user_id,))
        unread_count = int(cursor.fetchone()["cnt"] or 0)

        return jsonify({
            "status": "success",
            "message": "Notification marked as unread.",
            "unread_count": unread_count
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@notification_bp.route("/read-all", methods=["PATCH"])
def mark_all_read():
    """Mark all notifications as read for authenticated farmer."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("UPDATE notifications SET is_read = 1 WHERE user_id = %s AND is_read = 0", (user_id,))
        updated_count = cursor.rowcount
        connection.commit()

        return jsonify({
            "status": "success",
            "message": f"All notifications marked as read.",
            "updated_count": updated_count,
            "unread_count": 0
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@notification_bp.route("/<int:notification_id>", methods=["DELETE"])
def delete_notification(notification_id):
    """Delete individual notification owned by authenticated farmer."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT id FROM notifications WHERE id = %s AND user_id = %s", (notification_id, user_id))
        if not cursor.fetchone():
            return jsonify({"status": "error", "message": "Notification not found."}), 404

        cursor.execute("DELETE FROM notifications WHERE id = %s AND user_id = %s", (notification_id, user_id))
        connection.commit()

        cursor.execute("SELECT COUNT(*) AS cnt FROM notifications WHERE user_id = %s AND is_read = 0", (user_id,))
        unread_count = int(cursor.fetchone()["cnt"] or 0)

        return jsonify({
            "status": "success",
            "message": "Notification deleted successfully.",
            "unread_count": unread_count
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@notification_bp.route("/clear", methods=["DELETE"])
def clear_all_notifications():
    """Clear all notifications for the authenticated farmer."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("DELETE FROM notifications WHERE user_id = %s", (user_id,))
        deleted_count = cursor.rowcount
        connection.commit()

        return jsonify({
            "status": "success",
            "message": "All notifications cleared.",
            "deleted_count": deleted_count,
            "unread_count": 0
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@notification_bp.route("/preferences", methods=["GET"])
def get_preferences():
    """Get farmer's notification preferences."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        prefs = _get_preferences(cursor, user_id)
        return jsonify({
            "status": "success",
            "preferences": prefs
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@notification_bp.route("/preferences", methods=["PUT"])
def update_preferences():
    """Update farmer's notification preferences."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    data = request.get_json(silent=True) or {}
    crop_reminders = 1 if data.get("crop_reminders", True) else 0
    irrigation_alerts = 1 if data.get("irrigation_alerts", True) else 0
    weather_alerts = 1 if data.get("weather_alerts", True) else 0
    disease_reminders = 1 if data.get("disease_reminders", True) else 0
    activity_reminders = 1 if data.get("activity_reminders", True) else 0
    push_enabled = 1 if data.get("push_enabled", True) else 0

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            INSERT INTO notification_preferences (user_id, crop_reminders, irrigation_alerts, weather_alerts, disease_reminders, activity_reminders, push_enabled)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                crop_reminders = VALUES(crop_reminders),
                irrigation_alerts = VALUES(irrigation_alerts),
                weather_alerts = VALUES(weather_alerts),
                disease_reminders = VALUES(disease_reminders),
                activity_reminders = VALUES(activity_reminders),
                push_enabled = VALUES(push_enabled)
        """, (user_id, crop_reminders, irrigation_alerts, weather_alerts, disease_reminders, activity_reminders, push_enabled))
        connection.commit()

        updated_prefs = _get_preferences(cursor, user_id)
        return jsonify({
            "status": "success",
            "message": "Notification preferences updated successfully.",
            "preferences": updated_prefs
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# =============================================================================
# PWA PUSH NOTIFICATION SUBSCRIPTION ENDPOINTS
# =============================================================================

@notification_bp.route("/push-subscription", methods=["POST"])
def save_push_subscription():
    """Save or update farmer's browser push notification subscription."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    data = request.get_json(silent=True) or {}
    endpoint = str(data.get("endpoint", "")).strip()
    keys = data.get("keys", {}) if isinstance(data.get("keys"), dict) else {}
    p256dh = str(keys.get("p256dh") or data.get("p256dh") or "").strip()
    auth = str(keys.get("auth") or data.get("auth") or "").strip()
    user_agent = request.headers.get("User-Agent", data.get("user_agent", ""))[:250]

    if not endpoint or not p256dh or not auth:
        return jsonify({
            "status": "error",
            "message": "Missing required push subscription fields (endpoint, keys.p256dh, keys.auth)."
        }), 400

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            INSERT INTO push_subscriptions (user_id, endpoint, p256dh, auth, user_agent)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                p256dh = VALUES(p256dh),
                auth = VALUES(auth),
                user_agent = VALUES(user_agent)
        """, (user_id, endpoint, p256dh, auth, user_agent))
        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Push subscription saved successfully."
        }), 200
    except Exception as e:
        # Silently succeed if duplicate endpoint
        if connection:
            try:
                connection.rollback()
            except Exception:
                pass
        return jsonify({"status": "success", "message": "Push subscription registered."}), 200
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@notification_bp.route("/push-subscription", methods=["DELETE"])
def delete_push_subscription():
    """Remove farmer's browser push notification subscription."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("DELETE FROM push_subscriptions WHERE user_id = %s", (user_id,))
        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Push subscription removed."
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@notification_bp.route("/push-status", methods=["GET"])
def get_push_status():
    """Check push notification preference and subscription status."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        prefs = _get_preferences(cursor, user_id)
        cursor.execute("SELECT COUNT(*) as cnt FROM push_subscriptions WHERE user_id = %s", (user_id,))
        sub_count = int(cursor.fetchone()["cnt"] or 0)

        return jsonify({
            "status": "success",
            "push_enabled": prefs["push_enabled"],
            "has_subscription": sub_count > 0,
            "push_supported": True,
            "active_subscriptions_count": sub_count
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@notification_bp.route("/test-push", methods=["POST"])
def send_test_push():
    """Send or simulate a push notification for testing."""
    user_id, err_resp = _authenticate()
    if err_resp:
        return err_resp

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) as cnt FROM push_subscriptions WHERE user_id = %s", (user_id,))
        sub_count = int(cursor.fetchone()["cnt"] or 0)

        test_payload = {
            "title": "🌾 AgriSmart Farm Alert",
            "body": "This is a test notification verifying your active farm alert channel.",
            "url": "/farmer.html#notificationSection",
            "category": "system",
            "severity": "info"
        }
        return jsonify({
            "status": "success",
            "message": "Test notification dispatched.",
            "payload": test_payload,
            "push_payload": test_payload,
            "subscribers_notified": sub_count
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
