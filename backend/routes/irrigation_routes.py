"""AgriSmart Smart Irrigation Guidance Routes.

Provides crop-aware irrigation recommendations based on field measurements,
soil moisture, and ambient weather factors.
"""

from flask import Blueprint, jsonify, request
from config import get_db_connection
from utils.auth_tokens import get_user_id_from_token

irrigation_bp = Blueprint("irrigation", __name__, url_prefix="/api/irrigation")

# Agronomic reference parameters for common crops
CROP_PROFILES = {
    "rice": {
        "display_name": "Rice (Paddy)",
        "min_optimal": 70,
        "max_optimal": 85,
        "critical_threshold": 50,
        "water_sensitivity": "Very High",
        "notes": "Semi-aquatic crop requiring consistently high moisture or shallow standing water.",
    },
    "sugarcane": {
        "display_name": "Sugarcane",
        "min_optimal": 60,
        "max_optimal": 80,
        "critical_threshold": 45,
        "water_sensitivity": "High",
        "notes": "Long-duration crop with heavy biomass and high total water requirement.",
    },
    "potato": {
        "display_name": "Potato",
        "min_optimal": 60,
        "max_optimal": 75,
        "critical_threshold": 45,
        "water_sensitivity": "High",
        "notes": "Shallow root system; sensitive to moisture fluctuations and tuber cracking.",
    },
    "tomato": {
        "display_name": "Tomato",
        "min_optimal": 55,
        "max_optimal": 70,
        "critical_threshold": 40,
        "water_sensitivity": "High",
        "notes": "Moisture stress during flowering or fruiting causes blossom-end rot and fruit drop.",
    },
    "wheat": {
        "display_name": "Wheat",
        "min_optimal": 50,
        "max_optimal": 68,
        "critical_threshold": 35,
        "water_sensitivity": "Moderate",
        "notes": "Critical water stages are Crown Root Initiation (CRI) and flowering/grain filling.",
    },
    "maize": {
        "display_name": "Maize",
        "min_optimal": 50,
        "max_optimal": 68,
        "critical_threshold": 35,
        "water_sensitivity": "Moderate",
        "notes": "High water sensitivity during tasseling and silking stages.",
    },
    "cotton": {
        "display_name": "Cotton",
        "min_optimal": 45,
        "max_optimal": 65,
        "critical_threshold": 35,
        "water_sensitivity": "Moderate",
        "notes": "Deep tap root; susceptible to root asphyxiation if waterlogged.",
    },
    "soybean": {
        "display_name": "Soybean",
        "min_optimal": 48,
        "max_optimal": 65,
        "critical_threshold": 35,
        "water_sensitivity": "Moderate",
        "notes": "Sensitive to drought at pod initiation and seed development.",
    },
}

DEFAULT_PROFILE = {
    "display_name": "General Field Crop",
    "min_optimal": 50,
    "max_optimal": 70,
    "critical_threshold": 35,
    "water_sensitivity": "Moderate",
    "notes": "Standard agronomic threshold for loamy agricultural soil.",
}


def _get_crop_profile(crop_name):
    key = str(crop_name or "").strip().lower()
    for k, v in CROP_PROFILES.items():
        if k in key or key in k:
            return v
    return DEFAULT_PROFILE


@irrigation_bp.route("/recommend", methods=["POST"])
def recommend_irrigation():
    """Analyze crop, soil moisture, and weather to provide an irrigation recommendation.

    Endpoint: POST /api/irrigation/recommend
    Expects JSON payload with:
        crop: string (required)
        soilMoisture: float 0-100 (required)
        temperature: float -10 to 60 (required)
        humidity: float 0-100 (required)
        rainfall: float >= 0 (required)
        location: string (optional)
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "Request body must be a valid JSON object."
        }), 400

    # Support both snake_case and camelCase field names
    if "soil_moisture" in data and "soilMoisture" not in data:
        data["soilMoisture"] = data["soil_moisture"]

    # 1. Validate Crop
    crop = data.get("crop")
    if crop is None or not isinstance(crop, str) or not crop.strip():
        return jsonify({
            "status": "error",
            "message": "Crop name is required."
        }), 400
    crop_name = crop.strip()

    # 2. Validate Required Numeric Fields
    required_numerics = ["soilMoisture", "temperature", "humidity", "rainfall"]
    missing = [f for f in required_numerics if f not in data or data[f] is None or data[f] == ""]
    if missing:
        return jsonify({
            "status": "error",
            "message": f"Missing required measurements: {', '.join(missing)}."
        }), 400

    try:
        soil_moisture = float(data["soilMoisture"])
        temperature = float(data["temperature"])
        humidity = float(data["humidity"])
        rainfall = float(data["rainfall"])
    except (TypeError, ValueError):
        return jsonify({
            "status": "error",
            "message": "Soil moisture, temperature, humidity, and rainfall must be numeric values."
        }), 400

    # Range Validations
    if not (0 <= soil_moisture <= 100):
        return jsonify({
            "status": "error",
            "message": "Soil moisture must be a number between 0% and 100%."
        }), 400

    if not (-10 <= temperature <= 60):
        return jsonify({
            "status": "error",
            "message": "Temperature must be a number between -10°C and 60°C."
        }), 400

    if not (0 <= humidity <= 100):
        return jsonify({
            "status": "error",
            "message": "Humidity must be a number between 0% and 100%."
        }), 400

    if rainfall < 0:
        return jsonify({
            "status": "error",
            "message": "Recent rainfall must be a non-negative number (0 mm or greater)."
        }), 400

    location = str(data.get("location", "")).strip() or None

    # 3. Agronomic Irrigation Decision Logic
    profile = _get_crop_profile(crop_name)
    min_opt = profile["min_optimal"]
    max_opt = profile["max_optimal"]
    crit_thresh = profile["critical_threshold"]

    weather_advisories = []
    if temperature >= 35:
        weather_advisories.append(
            f"High heat conditions ({temperature:.1f}°C) accelerate evaporation. "
            "Irrigate strictly during early morning or sunset."
        )
    elif temperature <= 12:
        weather_advisories.append(
            f"Cool temperature ({temperature:.1f}°C) reduces evaporation rate. Soil dries slowly."
        )

    if humidity <= 30:
        weather_advisories.append(
            f"Low atmospheric humidity ({humidity:.1f}%) causes higher crop transpiration."
        )
    elif humidity >= 85 and temperature >= 22:
        weather_advisories.append(
            f"High humidity ({humidity:.1f}%) and warmth elevate fungal risk. Avoid wetting crop foliage directly."
        )

    if rainfall >= 25:
        weather_advisories.append(
            f"Substantial rainfall ({rainfall:.1f} mm) recorded recently. Ensure field drainage channels are unblocked."
        )

    weather_advisory_text = (
        " ".join(weather_advisories)
        if weather_advisories
        else "Weather conditions are within normal seasonal range for crop growth."
    )

    # Status Determination
    # Case A: Overwatered
    if soil_moisture > max_opt + 8 or (soil_moisture > max_opt and rainfall >= 15):
        status = "Overwatered"
        is_needed = False
        amount_mm = 0.0
        explanation = (
            f"Soil moisture ({soil_moisture:.1f}%) exceeds the optimal ceiling ({max_opt}%) for {crop_name}. "
            "Excess moisture can restrict root respiration and promote root diseases."
        )
        next_steps = [
            "Ensure field surface drainage is clear to prevent standing water pools.",
            "Pause all irrigation until soil dries down into the optimal range.",
            "Scout for signs of root rot or leaf yellowing caused by waterlogging."
        ]

    # Case B: Adequate
    elif soil_moisture >= min_opt:
        status = "Adequate"
        is_needed = False
        amount_mm = 0.0
        explanation = (
            f"Soil moisture ({soil_moisture:.1f}%) is within the optimal range ({min_opt}–{max_opt}%) for {crop_name}. "
            "Current soil water reserves are sufficient for healthy plant development."
        )
        next_steps = [
            "No irrigation is required at this time.",
            "Re-check soil moisture in 2 to 3 days or following hot, windy weather.",
            "Inspect mulch or ground cover to preserve existing soil moisture."
        ]

    # Case C: Recommended or Adequate via recent rain
    elif soil_moisture > crit_thresh:
        if rainfall >= 15:
            status = "Adequate"
            is_needed = False
            amount_mm = 0.0
            explanation = (
                f"Soil moisture ({soil_moisture:.1f}%) is slightly below target, but recent rainfall of "
                f"{rainfall:.1f} mm has provided sufficient topsoil replenishment. Irrigation can be deferred."
            )
            next_steps = [
                "Allow rainwater to percolate thoroughly into the root zone.",
                "Re-evaluate soil moisture tomorrow before scheduling any watering."
            ]
        else:
            status = "Recommended"
            is_needed = True
            # Estimated replenishment to reach mid-optimal zone
            amount_mm = round(max(15.0, (min_opt - soil_moisture) * 0.8), 1)
            explanation = (
                f"Soil moisture ({soil_moisture:.1f}%) has fallen below the optimal threshold ({min_opt}%) for {crop_name}. "
                "Applying irrigation within the next 24 to 48 hours is recommended to avoid moisture stress."
            )
            next_steps = [
                "Schedule irrigation during the early morning or evening to minimize evaporative loss.",
                "Deliver water uniformly around the crop root zone.",
                "Verify moisture penetration with a soil probe 2 hours after watering."
            ]

    # Case D: Urgent
    else:
        status = "Urgent"
        is_needed = True
        amount_mm = round(max(30.0, (min_opt - soil_moisture) * 1.0), 1)
        explanation = (
            f"Critical water deficit detected! Soil moisture ({soil_moisture:.1f}%) is at or below the critical "
            f"threshold ({crit_thresh}%) for {crop_name}. Immediate irrigation is needed to prevent wilting and yield damage."
        )
        next_steps = [
            "Irrigate immediately without delay.",
            "Ensure water penetrates to the active root depth (~30–50 cm).",
            "Avoid heavy chemical fertilizer applications until soil moisture is restored."
        ]

    # Formulate Water Quantity Structure
    if amount_mm > 0:
        litres_per_ha = int(amount_mm * 10000)
        water_quantity_display = f"~{amount_mm} mm depth ({litres_per_ha:,} Litres / hectare)"
    else:
        water_quantity_display = "0 mm depth (No additional water required)"

    recommendation = {
        "status": status,
        "is_irrigation_needed": is_needed,
        "water_quantity": {
            "amount_mm": amount_mm,
            "display": water_quantity_display,
            "units": "mm depth (1 mm = 10,000 Litres/hectare)",
            "assumptions": (
                "Estimated for an average 30–50 cm crop root zone in medium loam soil to bring moisture "
                "to field capacity. Actual requirements depend on field soil texture, slope, and distribution uniformity."
            ),
        },
        "duration_info": {
            "duration_hours": None,
            "explanation": (
                "Irrigation duration cannot be calculated without your field's specific flow rate "
                "(e.g., pump discharge in L/sec or drip emitter rate in L/h). "
                "Formula: Duration (hours) = Required Volume (Litres) / System Discharge Rate (Litres/hour)."
            ),
        },
        "explanation": explanation,
        "weather_advisory": weather_advisory_text,
        "next_steps": next_steps,
        "crop_info": {
            "crop": crop_name,
            "profile_name": profile["display_name"],
            "optimal_range": f"{min_opt}% – {max_opt}%",
            "water_sensitivity": profile["water_sensitivity"],
            "notes": profile["notes"],
        },
    }

    # 4. Authenticated Persistence (Save to irrigation_history if token present)
    history_saved = False
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):].strip()
        user_id = get_user_id_from_token(token)
        if user_id is not None:
            conn = None
            cur = None
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO irrigation_history
                        (user_id, crop, soil_moisture, temperature, humidity, rainfall, location,
                         recommendation_status, is_irrigation_needed, water_quantity_mm, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        crop_name,
                        soil_moisture,
                        temperature,
                        humidity,
                        rainfall,
                        location,
                        status,
                        1 if is_needed else 0,
                        amount_mm,
                        explanation[:500],
                    ),
                )
                conn.commit()
                history_saved = True
            except Exception as db_err:
                print(f"Could not save irrigation history: {db_err}")
                if conn:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
            finally:
                if cur:
                    cur.close()
                if conn:
                    conn.close()

    return jsonify({
        "status": "success",
        "recommendation": recommendation,
        "inputs": {
            "crop": crop_name,
            "soilMoisture": soil_moisture,
            "temperature": temperature,
            "humidity": humidity,
            "rainfall": rainfall,
            "location": location,
        },
        "history_saved": history_saved,
    }), 200


@irrigation_bp.route("/history", methods=["GET"])
def get_irrigation_history():
    """Return historical irrigation recommendations for the authenticated user.

    Endpoint: GET /api/irrigation/history
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({
            "status": "error",
            "message": "Authentication required. Please log in."
        }), 401

    token = auth_header[len("Bearer "):].strip()
    user_id = get_user_id_from_token(token)
    if user_id is None:
        return jsonify({
            "status": "error",
            "message": "Invalid or expired session. Please log in again."
        }), 401

    limit = 20
    try:
        limit = max(1, min(int(request.args.get("limit", 20)), 100))
    except (TypeError, ValueError):
        pass

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT id, crop, soil_moisture, temperature, humidity, rainfall, location,
                   recommendation_status, is_irrigation_needed, water_quantity_mm, notes, created_at
            FROM irrigation_history
            WHERE user_id = %s
            ORDER BY created_at DESC, id DESC
            LIMIT %s
            """,
            (user_id, limit),
        )
        rows = cur.fetchall()
        history = []
        for r in rows:
            created_at = r.get("created_at")
            history.append({
                "id": r["id"],
                "crop": r["crop"],
                "soil_moisture": float(r["soil_moisture"]),
                "temperature": float(r["temperature"]),
                "humidity": float(r["humidity"]),
                "rainfall": float(r["rainfall"]),
                "location": r.get("location"),
                "recommendation_status": r["recommendation_status"],
                "is_irrigation_needed": bool(r["is_irrigation_needed"]),
                "water_quantity_mm": float(r["water_quantity_mm"]) if r["water_quantity_mm"] is not None else 0.0,
                "notes": r.get("notes"),
                "created_at": created_at.isoformat() if created_at else None,
            })

        return jsonify({
            "status": "success",
            "count": len(history),
            "history": history
        }), 200

    except Exception as err:
        print(f"Failed to fetch irrigation history: {err}")
        return jsonify({
            "status": "error",
            "message": "Could not retrieve irrigation history."
        }), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
