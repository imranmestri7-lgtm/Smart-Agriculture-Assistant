"""AgriSmart Phase 10: IoT-Ready Smart Farm Monitoring Routes.

Supports:
- Secure hardware device ingestion (ESP32/Arduino) with device-specific API keys
- Sensor management (register, view, update, delete, regenerate key)
- Manual demo mode with isolated test records
- Historical sensor analytics and min/max/avg calculation
- Smart irrigation integration
- Automated threshold alerts and notifications
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
import hashlib
import json
import re
import secrets
from flask import Blueprint, jsonify, request
from config import get_db_connection
from utils.auth_tokens import get_user_id_from_token

iot_bp = Blueprint("iot", __name__, url_prefix="/api/iot")

SUPPORTED_SENSOR_TYPES = {
    "soil_moisture": {"label": "Soil Moisture", "unit": "%", "min_limit": 0.0, "max_limit": 100.0, "default_min": 20.0, "default_max": 80.0},
    "air_temp_humidity": {"label": "Air Temperature & Humidity", "unit": "°C / %", "min_limit": -40.0, "max_limit": 100.0, "default_min": 15.0, "default_max": 38.0},
    "air_temp": {"label": "Air Temperature", "unit": "°C", "min_limit": -40.0, "max_limit": 80.0, "default_min": 10.0, "default_max": 38.0},
    "air_humidity": {"label": "Air Humidity", "unit": "%", "min_limit": 0.0, "max_limit": 100.0, "default_min": 30.0, "default_max": 85.0},
    "soil_temp": {"label": "Soil Temperature", "unit": "°C", "min_limit": -20.0, "max_limit": 70.0, "default_min": 12.0, "default_max": 35.0},
    "water_level": {"label": "Water Level", "unit": "%", "min_limit": 0.0, "max_limit": 100.0, "default_min": 15.0, "default_max": 95.0},
}


# =========================================================================
# AUTHENTICATION & HELPERS
# =========================================================================

def _authenticate_farmer():
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
            "message": "Invalid or expired login token. Please log in again."
        }), 401)

    return user_id, None


def _authenticate_device(req, connection, cursor):
    """Authenticate hardware device via X-Device-Id and X-Device-Key or Authorization header."""
    device_id = req.headers.get("X-Device-Id")
    device_key = req.headers.get("X-Device-Key")

    if not device_key:
        auth = req.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            device_key = auth[len("Bearer "):].strip()

    # Fallback to JSON payload if headers omitted
    if req.is_json:
        data = req.get_json(silent=True) or {}
        if not device_id:
            device_id = data.get("device_id")
        if not device_key:
            device_key = data.get("device_key")

    if not device_id or not device_key:
        return None, (jsonify({
            "status": "error",
            "message": "Missing device credentials. Provide X-Device-Id and X-Device-Key headers."
        }), 401)

    cursor.execute("""
        SELECT s.id, s.user_id, s.farm_id, s.crop_id, s.device_id, s.device_key_hash,
               s.sensor_name, s.sensor_type, s.status, s.last_reading_at
        FROM sensors s
        WHERE s.device_id = %s
    """, (device_id,))
    sensor = cursor.fetchone()

    if not sensor:
        return None, (jsonify({
            "status": "error",
            "message": "Unregistered device. Please register this sensor in AgriSmart first."
        }), 401)

    expected_hash = sensor["device_key_hash"]
    computed_hash = hashlib.sha256(device_key.encode("utf-8")).hexdigest()

    if not secrets.compare_digest(expected_hash, computed_hash):
        return None, (jsonify({
            "status": "error",
            "message": "Invalid device credentials."
        }), 401)

    return sensor, None


def _compute_reading_status(sensor_type, value):
    """Compute status classification: Normal, Low, High, Critical."""
    try:
        val = float(value)
    except (ValueError, TypeError):
        return "Unknown"

    if sensor_type == "soil_moisture":
        if val < 10.0 or val > 90.0:
            return "Critical"
        if val < 20.0:
            return "Low"
        if val > 80.0:
            return "High"
        return "Normal"

    if sensor_type == "water_level":
        if val < 15.0:
            return "Critical"
        if val < 30.0:
            return "Low"
        return "Normal"

    if sensor_type in ("air_temp", "soil_temp"):
        if val < 0.0 or val > 42.0:
            return "Critical"
        if val < 10.0:
            return "Low"
        if val > 36.0:
            return "High"
        return "Normal"

    if sensor_type == "air_humidity":
        if val < 20.0 or val > 95.0:
            return "Critical"
        if val < 35.0:
            return "Low"
        if val > 85.0:
            return "High"
        return "Normal"

    return "Normal"


def _check_and_trigger_alerts(connection, cursor, sensor, sensor_type, value, is_demo=False):
    """Check sensor thresholds and generate notifications if limits are breached."""
    try:
        cursor.execute("""
            SELECT min_value, max_value, is_enabled
            FROM sensor_thresholds
            WHERE sensor_id = %s
        """, (sensor["id"],))
        threshold = cursor.fetchone()
        if not threshold or not threshold.get("is_enabled"):
            return

        min_val = float(threshold["min_value"]) if threshold.get("min_value") is not None else None
        max_val = float(threshold["max_value"]) if threshold.get("max_value") is not None else None
        val = float(value)
        sensor_name = sensor.get("sensor_name", "Sensor")
        user_id = sensor["user_id"]
        today_hour = datetime.now().strftime("%Y-%m-%d_%H")
        demo_prefix = "[Demo] " if is_demo else ""

        # Check low threshold
        if min_val is not None and val < min_val:
            unique_key = f"iot_low_{sensor['id']}_{sensor_type}_{today_hour}"
            title = f"{demo_prefix}⚠️ Low {SUPPORTED_SENSOR_TYPES.get(sensor_type, {}).get('label', sensor_type)} Alert"
            message = f"Sensor '{sensor_name}' reported a low reading of {val:.1f}{SUPPORTED_SENSOR_TYPES.get(sensor_type, {}).get('unit', '')} (below threshold {min_val:.1f})."
            severity = "danger" if val < (min_val * 0.6) else "warning"
            _create_iot_notification(connection, cursor, user_id, "irrigation" if "moist" in sensor_type else "system", title, message, severity, "#iot", unique_key)

        # Check high threshold
        elif max_val is not None and val > max_val:
            unique_key = f"iot_high_{sensor['id']}_{sensor_type}_{today_hour}"
            title = f"{demo_prefix}⚠️ High {SUPPORTED_SENSOR_TYPES.get(sensor_type, {}).get('label', sensor_type)} Warning"
            message = f"Sensor '{sensor_name}' reported an elevated reading of {val:.1f}{SUPPORTED_SENSOR_TYPES.get(sensor_type, {}).get('unit', '')} (above threshold {max_val:.1f})."
            severity = "warning"
            _create_iot_notification(connection, cursor, user_id, "irrigation" if "moist" in sensor_type else "system", title, message, severity, "#iot", unique_key)

    except Exception as e:
        print(f"Error checking sensor threshold alert: {e}")


def _create_iot_notification(connection, cursor, user_id, category, title, message, severity, link, unique_key):
    """Safely insert notification if not duplicate."""
    try:
        cursor.execute("SELECT id FROM notifications WHERE user_id = %s AND unique_key = %s", (user_id, unique_key))
        if cursor.fetchone():
            return
        cursor.execute("""
            INSERT INTO notifications (user_id, category, title, message, severity, link, unique_key, is_read, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 0, CURRENT_TIMESTAMP)
        """, (user_id, category, title, message, severity, link, unique_key))
        connection.commit()
    except Exception as e:
        print(f"Failed to record IoT notification: {e}")


# =========================================================================
# 1. HARDWARE DEVICE INGESTION API (ESP32 / Arduino)
# =========================================================================

@iot_bp.route("/ingest", methods=["POST"])
def ingest_sensor_reading():
    """
    Ingestion endpoint for hardware devices (ESP32, Arduino).
    Authenticates via X-Device-Id + X-Device-Key headers.
    Validates sensor values and units, inserts readings, and evaluates thresholds.
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        sensor, err = _authenticate_device(request, connection, cursor)
        if err:
            return err

        data = request.get_json(silent=True)
        if not data:
            return jsonify({"status": "error", "message": "Valid JSON body is required."}), 400

        # Parse timestamp
        raw_ts = data.get("timestamp")
        now_utc = datetime.now(timezone.utc)
        if raw_ts:
            try:
                dt = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)
                ts_utc = dt
            except Exception:
                return jsonify({"status": "error", "message": "Invalid timestamp format. Use ISO-8601 (e.g. 2026-10-31T09:50:00Z)."}), 400
        else:
            ts_utc = now_utc

        # Reject timestamps far in future (> 5 mins) or far in past (> 30 days)
        if ts_utc > now_utc + timedelta(minutes=5):
            return jsonify({"status": "error", "message": "Timestamp cannot be in the future."}), 400
        if ts_utc < now_utc - timedelta(days=30):
            return jsonify({"status": "error", "message": "Timestamp is too far in the past (> 30 days)."}), 400

        recorded_at = ts_utc.astimezone().replace(tzinfo=None)

        # Collect readings (support single or array payload)
        raw_readings = []
        if "readings" in data and isinstance(data["readings"], list):
            raw_readings = data["readings"]
        elif "value" in data:
            raw_readings = [{
                "sensor_type": data.get("sensor_type", sensor["sensor_type"]),
                "value": data.get("value"),
                "unit": data.get("unit")
            }]
        else:
            return jsonify({"status": "error", "message": "Reading value or 'readings' array is required."}), 400

        if not raw_readings:
            return jsonify({"status": "error", "message": "No valid readings provided."}), 400

        inserted_readings = []
        for r in raw_readings:
            s_type = r.get("sensor_type") or sensor["sensor_type"]
            val_raw = r.get("value")
            unit = r.get("unit") or SUPPORTED_SENSOR_TYPES.get(s_type, {}).get("unit", "")

            # Validate sensor type
            if s_type not in SUPPORTED_SENSOR_TYPES:
                return jsonify({"status": "error", "message": f"Unsupported sensor type: '{s_type}'."}), 400

            # Validate numeric value
            try:
                val = float(val_raw)
            except (ValueError, TypeError):
                return jsonify({"status": "error", "message": f"Sensor value must be a valid number, got {val_raw}."}), 400

            type_info = SUPPORTED_SENSOR_TYPES[s_type]
            if val < type_info["min_limit"] or val > type_info["max_limit"]:
                return jsonify({
                    "status": "error",
                    "message": f"Value {val} is outside valid physical limits for {type_info['label']} ({type_info['min_limit']} to {type_info['max_limit']})."
                }), 400

            cursor.execute("""
                INSERT INTO sensor_readings (sensor_id, user_id, sensor_type, value, unit, is_demo, recorded_at, created_at)
                VALUES (%s, %s, %s, %s, %s, 0, %s, CURRENT_TIMESTAMP)
            """, (sensor["id"], sensor["user_id"], s_type, val, unit, recorded_at))

            inserted_readings.append({"sensor_type": s_type, "value": val, "unit": unit})
            _check_and_trigger_alerts(connection, cursor, sensor, s_type, val, is_demo=False)

        # Update sensor last_reading_at and connected status
        cursor.execute("""
            UPDATE sensors
            SET status = 'connected', last_reading_at = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (recorded_at, sensor["id"]))

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Sensor reading recorded successfully.",
            "device_id": sensor["device_id"],
            "readings_count": len(inserted_readings),
            "readings": inserted_readings,
            "recorded_at": recorded_at.strftime("%Y-%m-%d %H:%M:%S")
        }), 200

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({"status": "error", "message": f"Database error during ingestion: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# =========================================================================
# 2. SENSOR MANAGEMENT ENDPOINTS (FARMER AUTHENTICATED)
# =========================================================================

@iot_bp.route("/sensors", methods=["GET"])
def list_sensors():
    """List all registered sensors belonging to the logged-in farmer with real-time status."""
    user_id, err = _authenticate_farmer()
    if err:
        return err

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT s.id, s.user_id, s.farm_id, s.crop_id, s.device_id, s.sensor_name, s.sensor_type,
                   s.status, s.last_reading_at, s.created_at, s.updated_at,
                   f.farm_name, f.location AS farm_location,
                   c.crop_name, c.variety AS crop_variety,
                   t.min_value, t.max_value, t.is_enabled AS threshold_enabled
            FROM sensors s
            JOIN farms f ON f.id = s.farm_id
            LEFT JOIN crops c ON c.id = s.crop_id
            LEFT JOIN sensor_thresholds t ON t.sensor_id = s.id
            WHERE s.user_id = %s
            ORDER BY s.created_at DESC
        """, (user_id,))
        sensors = cursor.fetchall() or []

        now = datetime.now()
        sensor_list = []
        for s in sensors:
            # Determine dynamic connection status
            last_reading = s.get("last_reading_at")
            if not last_reading:
                dyn_status = "disconnected"
            elif (now - last_reading).total_seconds() > (6 * 3600):
                dyn_status = "stale"
            else:
                dyn_status = "connected"

            # Query latest reading
            cursor.execute("""
                SELECT value, unit, is_demo, recorded_at
                FROM sensor_readings
                WHERE sensor_id = %s
                ORDER BY recorded_at DESC
                LIMIT 1
            """, (s["id"],))
            latest = cursor.fetchone()

            reading_info = None
            if latest:
                reading_info = {
                    "value": float(latest["value"]),
                    "unit": latest["unit"],
                    "is_demo": bool(latest["is_demo"]),
                    "reading_status": _compute_reading_status(s["sensor_type"], latest["value"]),
                    "recorded_at": latest["recorded_at"].strftime("%Y-%m-%d %H:%M:%S")
                }

            sensor_list.append({
                "id": s["id"],
                "device_id": s["device_id"],
                "sensor_name": s["sensor_name"],
                "sensor_type": s["sensor_type"],
                "sensor_type_label": SUPPORTED_SENSOR_TYPES.get(s["sensor_type"], {}).get("label", s["sensor_type"]),
                "unit": SUPPORTED_SENSOR_TYPES.get(s["sensor_type"], {}).get("unit", ""),
                "farm_id": s["farm_id"],
                "farm_name": s["farm_name"],
                "farm_location": s.get("farm_location") or "",
                "crop_id": s.get("crop_id"),
                "crop_name": s.get("crop_name") or "None assigned",
                "status": dyn_status,
                "last_reading_at": last_reading.strftime("%Y-%m-%d %H:%M:%S") if last_reading else None,
                "latest_reading": reading_info,
                "thresholds": {
                    "min_value": float(s["min_value"]) if s.get("min_value") is not None else None,
                    "max_value": float(s["max_value"]) if s.get("max_value") is not None else None,
                    "is_enabled": bool(s.get("threshold_enabled", 1))
                },
                "created_at": s["created_at"].strftime("%Y-%m-%d %H:%M:%S") if s.get("created_at") else None
            })

        return jsonify({
            "status": "success",
            "sensors": sensor_list,
            "total": len(sensor_list)
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@iot_bp.route("/sensors", methods=["POST"])
def register_sensor():
    """Register a new sensor and generate a cryptographically secure device key."""
    user_id, err = _authenticate_farmer()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    farm_id = data.get("farm_id")
    crop_id = data.get("crop_id") or None
    sensor_name = (data.get("sensor_name") or "").strip()
    sensor_type = (data.get("sensor_type") or "").strip()
    device_id = (data.get("device_id") or "").strip().upper()

    # Validation
    if not farm_id:
        return jsonify({"status": "error", "message": "Farm selection is required."}), 400
    if not sensor_name or len(sensor_name) < 2 or len(sensor_name) > 150:
        return jsonify({"status": "error", "message": "Sensor name must be between 2 and 150 characters."}), 400
    if sensor_type not in SUPPORTED_SENSOR_TYPES:
        return jsonify({"status": "error", "message": f"Invalid sensor type. Must be one of: {', '.join(SUPPORTED_SENSOR_TYPES.keys())}."}), 400
    if not device_id or not re.match(r"^[A-Z0-9_\-]{3,100}$", device_id):
        return jsonify({"status": "error", "message": "Device ID must be 3-100 characters alphanumeric, dashes, or underscores."}), 400

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Validate farm ownership
        cursor.execute("SELECT id FROM farms WHERE id = %s AND user_id = %s", (farm_id, user_id))
        if not cursor.fetchone():
            return jsonify({"status": "error", "message": "Selected farm does not exist or belong to your account."}), 400

        # Validate crop ownership if provided
        if crop_id:
            cursor.execute("SELECT id FROM crops WHERE id = %s AND user_id = %s", (crop_id, user_id))
            if not cursor.fetchone():
                return jsonify({"status": "error", "message": "Selected crop does not exist or belong to your account."}), 400

        # Validate device_id uniqueness
        cursor.execute("SELECT id FROM sensors WHERE device_id = %s", (device_id,))
        if cursor.fetchone():
            return jsonify({"status": "error", "message": f"Device ID '{device_id}' is already registered. Use a unique device ID."}), 409

        # Generate device key and hash
        raw_device_key = f"agy_dev_{secrets.token_urlsafe(24)}"
        key_hash = hashlib.sha256(raw_device_key.encode("utf-8")).hexdigest()

        # Insert sensor
        cursor.execute("""
            INSERT INTO sensors (user_id, farm_id, crop_id, device_id, device_key_hash, sensor_name, sensor_type, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'disconnected', CURRENT_TIMESTAMP)
        """, (user_id, farm_id, crop_id, device_id, key_hash, sensor_name, sensor_type))
        sensor_id = cursor.lastrowid

        # Insert default thresholds
        type_defaults = SUPPORTED_SENSOR_TYPES[sensor_type]
        min_threshold = data.get("min_value", type_defaults["default_min"])
        max_threshold = data.get("max_value", type_defaults["default_max"])

        cursor.execute("""
            INSERT INTO sensor_thresholds (sensor_id, user_id, min_value, max_value, is_enabled, created_at)
            VALUES (%s, %s, %s, %s, 1, CURRENT_TIMESTAMP)
        """, (sensor_id, user_id, min_threshold, max_threshold))

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Sensor registered successfully. Save the device key securely — it will NOT be displayed again.",
            "sensor": {
                "id": sensor_id,
                "device_id": device_id,
                "sensor_name": sensor_name,
                "sensor_type": sensor_type,
                "sensor_type_label": type_defaults["label"],
                "device_key": raw_device_key,  # Returned ONCE on creation
                "status": "disconnected"
            }
        }), 201

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@iot_bp.route("/sensors/<int:sensor_id>", methods=["PUT"])
def update_sensor(sensor_id):
    """Update sensor configuration (name, farm, crop, thresholds)."""
    user_id, err = _authenticate_farmer()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT id FROM sensors WHERE id = %s AND user_id = %s", (sensor_id, user_id))
        if not cursor.fetchone():
            return jsonify({"status": "error", "message": "Sensor not found or unauthorized."}), 404

        sensor_name = data.get("sensor_name")
        farm_id = data.get("farm_id")
        crop_id = data.get("crop_id")

        if sensor_name:
            sensor_name = sensor_name.strip()
            if len(sensor_name) < 2 or len(sensor_name) > 150:
                return jsonify({"status": "error", "message": "Sensor name must be between 2 and 150 characters."}), 400
            cursor.execute("UPDATE sensors SET sensor_name = %s WHERE id = %s", (sensor_name, sensor_id))

        if farm_id:
            cursor.execute("SELECT id FROM farms WHERE id = %s AND user_id = %s", (farm_id, user_id))
            if not cursor.fetchone():
                return jsonify({"status": "error", "message": "Invalid farm ID."}), 400
            cursor.execute("UPDATE sensors SET farm_id = %s WHERE id = %s", (farm_id, sensor_id))

        if crop_id is not None:
            if crop_id != "" and crop_id != 0:
                cursor.execute("SELECT id FROM crops WHERE id = %s AND user_id = %s", (crop_id, user_id))
                if not cursor.fetchone():
                    return jsonify({"status": "error", "message": "Invalid crop ID."}), 400
                cursor.execute("UPDATE sensors SET crop_id = %s WHERE id = %s", (crop_id, sensor_id))
            else:
                cursor.execute("UPDATE sensors SET crop_id = NULL WHERE id = %s", (sensor_id,))

        # Update thresholds
        min_val = data.get("min_value")
        max_val = data.get("max_value")
        is_enabled = data.get("threshold_enabled")

        if min_val is not None or max_val is not None or is_enabled is not None:
            cursor.execute("SELECT id FROM sensor_thresholds WHERE sensor_id = %s", (sensor_id,))
            exists = cursor.fetchone()
            if exists:
                updates = []
                params = []
                if min_val is not None:
                    updates.append("min_value = %s")
                    params.append(float(min_val))
                if max_val is not None:
                    updates.append("max_value = %s")
                    params.append(float(max_val))
                if is_enabled is not None:
                    updates.append("is_enabled = %s")
                    params.append(1 if is_enabled else 0)
                if updates:
                    params.append(sensor_id)
                    cursor.execute(f"UPDATE sensor_thresholds SET {', '.join(updates)} WHERE sensor_id = %s", tuple(params))
            else:
                cursor.execute("""
                    INSERT INTO sensor_thresholds (sensor_id, user_id, min_value, max_value, is_enabled)
                    VALUES (%s, %s, %s, %s, %s)
                """, (sensor_id, user_id, min_val, max_val, 1 if is_enabled is not False else 0))

        connection.commit()
        return jsonify({"status": "success", "message": "Sensor details updated successfully."}), 200

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@iot_bp.route("/sensors/<int:sensor_id>/regenerate-key", methods=["POST"])
def regenerate_device_key(sensor_id):
    """Regenerate a new device API key for the sensor (e.g. if key was leaked or rotated)."""
    user_id, err = _authenticate_farmer()
    if err:
        return err

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT id, device_id FROM sensors WHERE id = %s AND user_id = %s", (sensor_id, user_id))
        sensor = cursor.fetchone()
        if not sensor:
            return jsonify({"status": "error", "message": "Sensor not found or unauthorized."}), 404

        new_device_key = f"agy_dev_{secrets.token_urlsafe(24)}"
        new_key_hash = hashlib.sha256(new_device_key.encode("utf-8")).hexdigest()

        cursor.execute("UPDATE sensors SET device_key_hash = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (new_key_hash, sensor_id))
        connection.commit()

        return jsonify({
            "status": "success",
            "message": "New device key generated. Flash this key to your device immediately.",
            "device_id": sensor["device_id"],
            "device_key": new_device_key
        }), 200

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@iot_bp.route("/sensors/<int:sensor_id>", methods=["DELETE"])
def delete_sensor(sensor_id):
    """Remove a sensor and its associated readings."""
    user_id, err = _authenticate_farmer()
    if err:
        return err

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT id, sensor_name FROM sensors WHERE id = %s AND user_id = %s", (sensor_id, user_id))
        sensor = cursor.fetchone()
        if not sensor:
            return jsonify({"status": "error", "message": "Sensor not found or unauthorized."}), 404

        cursor.execute("DELETE FROM sensors WHERE id = %s", (sensor_id,))
        connection.commit()

        return jsonify({
            "status": "success",
            "message": f"Sensor '{sensor['sensor_name']}' has been removed."
        }), 200

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# =========================================================================
# 3. MANUAL DEMO MODE ENDPOINTS
# =========================================================================

@iot_bp.route("/sensors/<int:sensor_id>/demo", methods=["POST"])
def inject_demo_reading(sensor_id):
    """Inject a manual demo reading for testing without hardware."""
    user_id, err = _authenticate_farmer()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    val_raw = data.get("value")
    if val_raw is None:
        return jsonify({"status": "error", "message": "Reading value is required."}), 400

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT id, user_id, sensor_name, sensor_type FROM sensors WHERE id = %s AND user_id = %s", (sensor_id, user_id))
        sensor = cursor.fetchone()
        if not sensor:
            return jsonify({"status": "error", "message": "Sensor not found or unauthorized."}), 404

        s_type = data.get("sensor_type") or sensor["sensor_type"]
        if s_type not in SUPPORTED_SENSOR_TYPES:
            return jsonify({"status": "error", "message": f"Unsupported sensor type: '{s_type}'."}), 400

        try:
            val = float(val_raw)
        except (ValueError, TypeError):
            return jsonify({"status": "error", "message": "Value must be a valid number."}), 400

        type_info = SUPPORTED_SENSOR_TYPES[s_type]
        if val < type_info["min_limit"] or val > type_info["max_limit"]:
            return jsonify({
                "status": "error",
                "message": f"Value {val} is outside limits ({type_info['min_limit']} to {type_info['max_limit']})."
            }), 400

        unit = data.get("unit") or type_info["unit"]
        now = datetime.now()

        cursor.execute("""
            INSERT INTO sensor_readings (sensor_id, user_id, sensor_type, value, unit, is_demo, recorded_at, created_at)
            VALUES (%s, %s, %s, %s, %s, 1, %s, CURRENT_TIMESTAMP)
        """, (sensor_id, user_id, s_type, val, unit, now))

        cursor.execute("""
            UPDATE sensors
            SET status = 'connected', last_reading_at = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (now, sensor_id))

        connection.commit()

        # Check thresholds with [Demo] prefix
        _check_and_trigger_alerts(connection, cursor, sensor, s_type, val, is_demo=True)

        return jsonify({
            "status": "success",
            "message": "Demo sensor reading recorded successfully.",
            "is_demo": True,
            "reading": {
                "sensor_id": sensor_id,
                "sensor_type": s_type,
                "value": val,
                "unit": unit,
                "recorded_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                "status": _compute_reading_status(s_type, val)
            }
        }), 201

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@iot_bp.route("/sensors/<int:sensor_id>/demo", methods=["DELETE"])
def clear_demo_readings(sensor_id):
    """Delete all demo records (is_demo=1) for a sensor."""
    user_id, err = _authenticate_farmer()
    if err:
        return err

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT id FROM sensors WHERE id = %s AND user_id = %s", (sensor_id, user_id))
        if not cursor.fetchone():
            return jsonify({"status": "error", "message": "Sensor not found or unauthorized."}), 404

        cursor.execute("DELETE FROM sensor_readings WHERE sensor_id = %s AND is_demo = 1", (sensor_id,))
        deleted_count = cursor.rowcount

        # Recalculate last_reading_at from remaining hardware readings
        cursor.execute("""
            SELECT recorded_at FROM sensor_readings
            WHERE sensor_id = %s
            ORDER BY recorded_at DESC LIMIT 1
        """, (sensor_id,))
        latest = cursor.fetchone()
        new_last = latest["recorded_at"] if latest else None
        new_status = "connected" if new_last else "disconnected"

        cursor.execute("UPDATE sensors SET last_reading_at = %s, status = %s WHERE id = %s", (new_last, new_status, sensor_id))
        connection.commit()

        return jsonify({
            "status": "success",
            "message": f"Deleted {deleted_count} demo readings.",
            "cleared_count": deleted_count
        }), 200

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# =========================================================================
# 4. SENSOR HISTORY & ANALYTICS
# =========================================================================

@iot_bp.route("/sensors/<int:sensor_id>/history", methods=["GET"])
def get_sensor_history(sensor_id):
    """Fetch historical sensor readings with min, max, average statistics and range filtering."""
    user_id, err = _authenticate_farmer()
    if err:
        return err

    time_range = request.args.get("range", "24h").lower()
    include_demo = request.args.get("include_demo", "true").lower() in ("true", "1")

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT s.id, s.sensor_name, s.sensor_type, s.device_id, f.farm_name, c.crop_name
            FROM sensors s
            JOIN farms f ON f.id = s.farm_id
            LEFT JOIN crops c ON c.id = s.crop_id
            WHERE s.id = %s AND s.user_id = %s
        """, (sensor_id, user_id))
        sensor = cursor.fetchone()
        if not sensor:
            return jsonify({"status": "error", "message": "Sensor not found or unauthorized."}), 404

        # Compute time filter
        now = datetime.now()
        since_time = None
        if time_range == "24h":
            since_time = now - timedelta(hours=24)
        elif time_range == "7d":
            since_time = now - timedelta(days=7)
        elif time_range == "30d":
            since_time = now - timedelta(days=30)

        query = """
            SELECT id, sensor_type, value, unit, is_demo, recorded_at
            FROM sensor_readings
            WHERE sensor_id = %s
        """
        params = [sensor_id]

        if not include_demo:
            query += " AND is_demo = 0"
        if since_time:
            query += " AND recorded_at >= %s"
            params.append(since_time)

        query += " ORDER BY recorded_at ASC"

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall() or []

        if not rows:
            return jsonify({
                "status": "success",
                "sensor": {
                    "id": sensor["id"],
                    "name": sensor["sensor_name"],
                    "type": sensor["sensor_type"],
                    "farm": sensor["farm_name"],
                    "crop": sensor["crop_name"] or "None"
                },
                "range": time_range,
                "readings": [],
                "stats": {
                    "count": 0,
                    "min": None,
                    "max": None,
                    "avg": None,
                    "unit": SUPPORTED_SENSOR_TYPES.get(sensor["sensor_type"], {}).get("unit", "")
                }
            }), 200

        values = [float(r["value"]) for r in rows]
        min_v = min(values)
        max_v = max(values)
        avg_v = round(sum(values) / len(values), 1)

        readings_out = []
        for r in rows:
            readings_out.append({
                "id": r["id"],
                "value": float(r["value"]),
                "unit": r["unit"],
                "is_demo": bool(r["is_demo"]),
                "recorded_at": r["recorded_at"].strftime("%Y-%m-%d %H:%M:%S")
            })

        return jsonify({
            "status": "success",
            "sensor": {
                "id": sensor["id"],
                "name": sensor["sensor_name"],
                "type": sensor["sensor_type"],
                "farm": sensor["farm_name"],
                "crop": sensor["crop_name"] or "None"
            },
            "range": time_range,
            "readings": readings_out,
            "stats": {
                "count": len(values),
                "min": min_v,
                "max": max_v,
                "avg": avg_v,
                "unit": rows[0]["unit"] if rows else ""
            }
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# =========================================================================
# 5. DASHBOARD OVERVIEW & METRICS
# =========================================================================

@iot_bp.route("/overview", methods=["GET"])
def get_monitoring_overview():
    """Retrieve summarized sensor statistics and latest readings across categories."""
    user_id, err = _authenticate_farmer()
    if err:
        return err

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT id, last_reading_at FROM sensors WHERE user_id = %s", (user_id,))
        sensors = cursor.fetchall() or []

        now = datetime.now()
        total_sensors = len(sensors)
        connected_count = 0
        stale_count = 0
        disconnected_count = 0

        for s in sensors:
            last = s.get("last_reading_at")
            if not last:
                disconnected_count += 1
            elif (now - last).total_seconds() > (6 * 3600):
                stale_count += 1
            else:
                connected_count += 1

        # Fetch latest reading for each primary monitoring category
        categories = ["soil_moisture", "air_temp", "air_humidity", "soil_temp", "water_level"]
        latest_readings = {}

        for cat in categories:
            cursor.execute("""
                SELECT r.value, r.unit, r.is_demo, r.recorded_at,
                       s.sensor_name, s.sensor_type, f.farm_name, c.crop_name
                FROM sensor_readings r
                JOIN sensors s ON s.id = r.sensor_id
                JOIN farms f ON f.id = s.farm_id
                LEFT JOIN crops c ON c.id = s.crop_id
                WHERE r.user_id = %s AND (r.sensor_type = %s OR (s.sensor_type = %s AND r.sensor_type = %s))
                ORDER BY r.recorded_at DESC
                LIMIT 1
            """, (user_id, cat, cat, cat))
            row = cursor.fetchone()

            if row:
                val = float(row["value"])
                latest_readings[cat] = {
                    "has_reading": True,
                    "value": val,
                    "unit": row["unit"],
                    "is_demo": bool(row["is_demo"]),
                    "status": _compute_reading_status(cat, val),
                    "sensor_name": row["sensor_name"],
                    "farm_name": row["farm_name"],
                    "crop_name": row.get("crop_name") or "All Fields",
                    "recorded_at": row["recorded_at"].strftime("%Y-%m-%d %H:%M:%S")
                }
            else:
                latest_readings[cat] = {
                    "has_reading": False,
                    "value": None,
                    "unit": SUPPORTED_SENSOR_TYPES.get(cat, {}).get("unit", ""),
                    "status": "No Sensor",
                    "sensor_name": "Not connected",
                    "farm_name": "-",
                    "crop_name": "-",
                    "recorded_at": None,
                    "is_demo": False
                }

        return jsonify({
            "status": "success",
            "summary": {
                "total_sensors": total_sensors,
                "connected": connected_count,
                "stale": stale_count,
                "disconnected": disconnected_count
            },
            "latest_readings": latest_readings,
            "last_synced": now.strftime("%Y-%m-%d %H:%M:%S")
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# =========================================================================
# 6. SMART IRRIGATION INTEGRATION ENDPOINT
# =========================================================================

@iot_bp.route("/irrigation-sync", methods=["GET"])
def get_irrigation_sensor_sync():
    """
    Returns latest validated soil moisture reading for irrigation recommendation prefill.
    Distinguishes real sensor measurements from demo records.
    """
    user_id, err = _authenticate_farmer()
    if err:
        return err

    crop_name = request.args.get("crop", "").strip()
    farm_id = request.args.get("farm_id")

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT r.id, r.value, r.unit, r.is_demo, r.recorded_at,
                   s.sensor_name, f.farm_name, c.crop_name
            FROM sensor_readings r
            JOIN sensors s ON s.id = r.sensor_id
            JOIN farms f ON f.id = s.farm_id
            LEFT JOIN crops c ON c.id = s.crop_id
            WHERE r.user_id = %s AND r.sensor_type = 'soil_moisture'
        """
        params = [user_id]

        if crop_name:
            query += " AND (c.crop_name = %s OR s.sensor_name LIKE %s)"
            params.extend([crop_name, f"%{crop_name}%"])

        if farm_id:
            query += " AND s.farm_id = %s"
            params.append(farm_id)

        # Prioritize real hardware readings over demo readings
        query += " ORDER BY r.is_demo ASC, r.recorded_at DESC LIMIT 1"

        cursor.execute(query, tuple(params))
        row = cursor.fetchone()

        if not row:
            return jsonify({
                "status": "success",
                "has_sensor_data": False,
                "message": "No soil moisture sensor found for this crop/farm."
            }), 200

        val = float(row["value"])
        return jsonify({
            "status": "success",
            "has_sensor_data": True,
            "soil_moisture": val,
            "unit": row["unit"],
            "sensor_name": row["sensor_name"],
            "farm_name": row["farm_name"],
            "crop_name": row.get("crop_name") or "General Field",
            "is_demo": bool(row["is_demo"]),
            "recorded_at": row["recorded_at"].strftime("%Y-%m-%d %H:%M:%S"),
            "status_label": _compute_reading_status("soil_moisture", val)
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Database error: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
