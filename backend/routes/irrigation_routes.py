"""AgriSmart Smart Irrigation Guidance Routes.

Provides crop-aware, soil-aware, and growth-stage-aware irrigation recommendations
based on field measurements, soil moisture, ambient weather factors, and upcoming rainfall forecasts.
"""

import os
import requests
from flask import Blueprint, jsonify, request
from config import get_db_connection
from utils.auth_tokens import get_user_id_from_token

irrigation_bp = Blueprint("irrigation", __name__, url_prefix="/api/irrigation")

WEATHER_API_BASE_URL = "https://api.weatherapi.com/v1"

# =============================================================================
# AGRONOMIC REFERENCE DATA
# =============================================================================

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
    "onion": {
        "display_name": "Onion",
        "min_optimal": 55,
        "max_optimal": 70,
        "critical_threshold": 40,
        "water_sensitivity": "High",
        "notes": "Shallow root bulb crop; requires regular shallow watering to avoid splitting.",
    },
    "groundnut": {
        "display_name": "Groundnut / Peanut",
        "min_optimal": 45,
        "max_optimal": 65,
        "critical_threshold": 35,
        "water_sensitivity": "Moderate",
        "notes": "Critical water stage is peg penetration and pod development.",
    },
    "chili": {
        "display_name": "Chili / Pepper",
        "min_optimal": 50,
        "max_optimal": 68,
        "critical_threshold": 38,
        "water_sensitivity": "High",
        "notes": "Sensitive to waterlogging; flowering drop occurs under moisture swings.",
    },
    "banana": {
        "display_name": "Banana",
        "min_optimal": 65,
        "max_optimal": 80,
        "critical_threshold": 50,
        "water_sensitivity": "Very High",
        "notes": "Large leaf area causes high transpiration; requires frequent copious irrigation.",
    },
    "gram": {
        "display_name": "Gram / Chickpea",
        "min_optimal": 40,
        "max_optimal": 60,
        "critical_threshold": 30,
        "water_sensitivity": "Low-Moderate",
        "notes": "Drought-hardy pulse crop; excess water causes excessive vegetative growth and root rot.",
    },
}

DEFAULT_CROP_PROFILE = {
    "display_name": "General Field Crop",
    "min_optimal": 50,
    "max_optimal": 70,
    "critical_threshold": 35,
    "water_sensitivity": "Moderate",
    "notes": "Standard agronomic threshold for loamy agricultural soil.",
}

SOIL_PROFILES = {
    "sandy": {
        "key": "sandy",
        "display_name": "Sandy Soil",
        "name_mr": "वाळूयुक्त जमीन",
        "name_hi": "रेतीली मिट्टी",
        "retention": "Low (60–90 mm/m)",
        "infiltration": "Rapid (>25 mm/hr)",
        "factor": 0.70,
        "threshold_adj": 3.0,
        "advice": "Sandy soil drains rapidly. Apply lighter, more frequent irrigations to prevent nutrients from leaching beyond root reach.",
        "tips": [
            "Apply water in short, frequent intervals rather than heavy single doses.",
            "Incorporate organic compost or farmyard manure to enhance water retention capacity.",
            "Use straw or biodegradable mulching to reduce high surface evaporation."
        ]
    },
    "loamy": {
        "key": "loamy",
        "display_name": "Loamy Soil",
        "name_mr": "गाळाची / सुपीक जमीन",
        "name_hi": "दोमट मिट्टी",
        "retention": "Optimal / Balanced (140–180 mm/m)",
        "infiltration": "Moderate (10–20 mm/hr)",
        "factor": 1.0,
        "threshold_adj": 0.0,
        "advice": "Loamy soil offers ideal moisture retention and aeration balance for agricultural crops.",
        "tips": [
            "Maintain consistent moisture levels around the active root depth.",
            "Periodic soil aeration between watering cycles preserves root health.",
            "Drip irrigation provides maximum water efficiency in loamy soil."
        ]
    },
    "clay": {
        "key": "clay",
        "display_name": "Clay Soil",
        "name_mr": "चिकणमाती जमीन",
        "name_hi": "चिकनी मिट्टी",
        "retention": "Very High (180–220 mm/m)",
        "infiltration": "Slow (<5 mm/hr)",
        "factor": 1.25,
        "threshold_adj": -3.0,
        "advice": "Clay soil holds water strongly but has slow drainage. Irrigate slowly to avoid waterlogging and root asphyxiation.",
        "tips": [
            "Allow topsoil to aerate between irrigations to avoid root suffocation and damping-off.",
            "Apply water at a slow discharge rate to prevent surface runoff and ponding.",
            "Avoid walking or operating heavy machinery on wet clay to prevent severe soil compaction."
        ]
    },
    "black": {
        "key": "black",
        "display_name": "Black Cotton Soil (Regur)",
        "name_mr": "काळी कापशी जमीन (रेगूर)",
        "name_hi": "काली मिट्टी (रेगुर)",
        "retention": "Very High (190–230 mm/m)",
        "infiltration": "Very Slow (<4 mm/hr)",
        "factor": 1.20,
        "threshold_adj": -2.0,
        "advice": "Black cotton soil expands when wet and develops deep fissures when dry. Avoid heavy flooding; adopt furrow or drip irrigation.",
        "tips": [
            "Use broad-bed and furrow (BBF) systems or drip lines to control water distribution.",
            "Do not allow soil to crack excessively before irrigating, as cracks shear tender root systems.",
            "Ensure field drainage outlets are kept open to evacuate heavy monsoon and irrigation runoff."
        ]
    },
    "red": {
        "key": "red",
        "display_name": "Red / Laterite Soil",
        "name_mr": "तांबडी जमीन",
        "name_hi": "लाल मिट्टी",
        "retention": "Moderate (100–130 mm/m)",
        "infiltration": "Good (15–25 mm/hr)",
        "factor": 0.85,
        "threshold_adj": 2.0,
        "advice": "Red soils drain freely and are moderately porous. Regular moderate water doses maintain steady crop growth.",
        "tips": [
            "Split irrigation applications into moderate doses to sustain uniform root moisture.",
            "Apply organic mulches to conserve moisture in hot weather.",
            "Supplement with organic compost to build soil water-holding structure."
        ]
    },
    "silt": {
        "key": "silt",
        "display_name": "Silt Soil",
        "name_mr": "गाळ जमीन",
        "name_hi": "सिल्ट मिट्टी",
        "retention": "High (160–200 mm/m)",
        "infiltration": "Moderate (8–15 mm/hr)",
        "factor": 1.05,
        "threshold_adj": 0.0,
        "advice": "Silt soil holds significant moisture but can form surface crusts after drying.",
        "tips": [
            "Lightly disturb the topsoil crust after watering to preserve infiltration.",
            "Apply uniform irrigation across the field.",
            "Monitor sub-surface moisture before re-watering."
        ]
    }
}

GROWTH_STAGES = {
    "seedling": {
        "key": "seedling",
        "display_name": "Newly Planted / Seedling",
        "name_mr": "रोपावस्था / नवीन लागवड",
        "name_hi": "नई बुवाई / अंकुरण",
        "depth_factor": 0.50,
        "threshold_boost": 2.0,
        "critical": False,
        "advice": "Shallow root system (10–15 cm). Needs frequent, light moisture to support germination and prevent crusting.",
        "tips": [
            "Irrigate lightly with fine droplets or micro-sprinklers to avoid displacing seeds or tender seedlings.",
            "Keep topsoil damp, avoiding standing water puddles that lead to damping-off fungus."
        ]
    },
    "vegetative": {
        "key": "vegetative",
        "display_name": "Vegetative / Growth Stage",
        "name_mr": "शाकीय वाढ अवस्था",
        "name_hi": "वानस्पतिक वृद्धि",
        "depth_factor": 0.85,
        "threshold_boost": 0.0,
        "critical": False,
        "advice": "Active canopy, leaf, and root expansion. Steady moisture is required to sustain vegetative development.",
        "tips": [
            "Encourage deep root penetration by watering thoroughly rather than superficial wetting.",
            "Inspect foliage regularly for signs of midday moisture stress or leaf curling."
        ]
    },
    "flowering": {
        "key": "flowering",
        "display_name": "Flowering / Bloom (Critical)",
        "name_mr": "फुलोरा अवस्था (अत्यंत संवेदनशील)",
        "name_hi": "फूल आने की अवस्था (अति संवेदनशील)",
        "depth_factor": 1.15,
        "threshold_boost": 5.0,
        "critical": True,
        "advice": "MOST CRITICAL STAGE: Any moisture stress during flowering causes flower abortion, poor pollination, and dramatic yield loss.",
        "tips": [
            "CRITICAL PRIORITY: Never let soil dry out below optimal levels during flowering.",
            "Avoid overhead sprinkler watering during peak bloom to avoid washing pollen off blossoms.",
            "Irrigate during early morning to provide adequate daytime turgor."
        ]
    },
    "fruiting": {
        "key": "fruiting",
        "display_name": "Fruiting / Pod / Grain Filling",
        "name_mr": "फळधारणा / दाणे भरणे",
        "name_hi": "फल / दाना भराव अवस्था",
        "depth_factor": 1.20,
        "threshold_boost": 2.0,
        "critical": False,
        "advice": "Heavy water demand for fruit sizing and grain filling. Steady moisture prevents fruit splitting and blossom-end rot.",
        "tips": [
            "Maintain uniform moisture; alternating dry and wet periods triggers fruit cracking and blossom-end rot.",
            "Support heavy crop load with consistent drip or furrow scheduling."
        ]
    },
    "near_harvest": {
        "key": "near_harvest",
        "display_name": "Near Harvest / Maturation",
        "name_mr": "पक्वता / काढणी पूर्व अवस्था",
        "name_hi": "परिपक्वता / कटाई पूर्व",
        "depth_factor": 0.40,
        "threshold_boost": -8.0,
        "critical": False,
        "advice": "Ripening stage: Taper or withhold irrigation 7–14 days before harvest to enhance crop quality, sweetness, and storability.",
        "tips": [
            "Gradually taper or stop irrigation to allow crop maturity and ease field machinery access.",
            "Withholding water prior to harvest concentrates sugars/solids and prevents harvest rotting."
        ]
    }
}


def _get_crop_profile(crop_name):
    key = str(crop_name or "").strip().lower()
    for k, v in CROP_PROFILES.items():
        if k in key or key in k:
            return v
    return DEFAULT_CROP_PROFILE


def _get_soil_profile(soil_type):
    key = str(soil_type or "").strip().lower()
    for k, v in SOIL_PROFILES.items():
        if k in key:
            return v
    return SOIL_PROFILES["loamy"]


def _get_stage_profile(growth_stage):
    key = str(growth_stage or "").strip().lower()
    if "seedling" in key or "plant" in key or "sow" in key or "अंकुर" in key or "रोप" in key:
        return GROWTH_STAGES["seedling"]
    if "flower" in key or "bloom" in key or "silk" in key or "फूल" in key or "फुल" in key:
        return GROWTH_STAGES["flowering"]
    if "fruit" in key or "pod" in key or "grain" in key or "bulb" in key or "फल" in key or "फळ" in key or "दाण" in key:
        return GROWTH_STAGES["fruiting"]
    if "harvest" in key or "matur" in key or "ripen" in key or "काढणी" in key or "कटाई" in key or "पक्व" in key:
        return GROWTH_STAGES["near_harvest"]
    return GROWTH_STAGES["vegetative"]


def _fetch_live_weather(location_query):
    """Attempt to fetch live temperature, humidity, rainfall, and forecast from WeatherAPI proxy."""
    api_key = os.getenv("WEATHER_API_KEY", "").strip()
    if not api_key or not location_query:
        return None

    try:
        url = f"{WEATHER_API_BASE_URL}/forecast.json"
        params = {
            "key": api_key,
            "q": location_query,
            "days": 2,
            "aqi": "no",
            "alerts": "no"
        }
        res = requests.get(url, params=params, timeout=5)
        if not res.ok:
            return None
        data = res.json()
        curr = data.get("current", {})
        forecast_days = data.get("forecast", {}).get("forecastday", [])

        forecast_rain_mm = 0.0
        if forecast_days:
            # Sum precip of next day or day 0 remaining
            for fday in forecast_days[:2]:
                forecast_rain_mm += float(fday.get("day", {}).get("totalprecip_mm") or 0.0)

        return {
            "temperature": float(curr.get("temp_c", 25.0)),
            "humidity": float(curr.get("humidity", 50.0)),
            "rainfall": float(curr.get("precip_mm", 0.0)),
            "forecast_rain_mm": round(forecast_rain_mm, 1),
            "condition": curr.get("condition", {}).get("text", "Clear"),
            "location_name": data.get("location", {}).get("name", location_query)
        }
    except Exception as err:
        print(f"Weather lookup fallback: {err}")
        return None


# =============================================================================
# SMART IRRIGATION RECOMMENDATION ENDPOINT
# =============================================================================

@irrigation_bp.route("/recommend", methods=["POST"])
def recommend_irrigation():
    """Analyze crop, growth stage, soil type, moisture, and weather forecast for smart irrigation.

    Endpoint: POST /api/irrigation/recommend
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "Request body must be a valid JSON object."
        }), 400

    # Support snake_case and camelCase field aliases
    if "soil_moisture" in data and "soilMoisture" not in data:
        data["soilMoisture"] = data["soil_moisture"]
    if "soil_type" in data and "soilType" not in data:
        data["soilType"] = data["soil_type"]
    if "growth_stage" in data and "growthStage" not in data:
        data["growthStage"] = data["growth_stage"]
    if "forecast_rain_mm" in data and "forecastRain" not in data:
        data["forecastRain"] = data["forecast_rain_mm"]

    # 1. Validate Crop
    crop = data.get("crop")
    if crop is None or not isinstance(crop, str) or not crop.strip():
        return jsonify({
            "status": "error",
            "message": "Crop name is required."
        }), 400
    crop_name = crop.strip()

    location = str(data.get("location", "")).strip() or None
    soil_type_input = str(data.get("soilType", "loamy")).strip()
    growth_stage_input = str(data.get("growthStage", "vegetative")).strip()

    # Check unmeasured soil moisture flag
    moisture_unmeasured = bool(
        data.get("moisture_unmeasured") or
        data.get("allow_unmeasured") or
        data.get("soilMoisture") == "unmeasured" or
        (data.get("soilMoisture") is None and data.get("allow_unmeasured"))
    )

    # 2. Check and parse numeric fields
    # If weather fields are missing, try live weather lookup if location is available
    weather_auto_fetched = False
    if ("temperature" not in data or "humidity" not in data or "rainfall" not in data) and location:
        weather_data = _fetch_live_weather(location)
        if weather_data:
            if "temperature" not in data or data["temperature"] is None or data["temperature"] == "":
                data["temperature"] = weather_data["temperature"]
            if "humidity" not in data or data["humidity"] is None or data["humidity"] == "":
                data["humidity"] = weather_data["humidity"]
            if "rainfall" not in data or data["rainfall"] is None or data["rainfall"] == "":
                data["rainfall"] = weather_data["rainfall"]
            if "forecastRain" not in data or data["forecastRain"] is None or data["forecastRain"] == "":
                data["forecastRain"] = weather_data["forecast_rain_mm"]
            weather_auto_fetched = True

    # Validate required measurements
    required_numerics = ["temperature", "humidity", "rainfall"]
    if not moisture_unmeasured:
        required_numerics.insert(0, "soilMoisture")

    missing = [f for f in required_numerics if f not in data or data[f] is None or data[f] == ""]
    if missing:
        return jsonify({
            "status": "error",
            "message": f"Missing required measurements: {', '.join(missing)}."
        }), 400

    # Parse numerics
    try:
        soil_moisture = None
        if not moisture_unmeasured:
            soil_moisture = float(data["soilMoisture"])

        temperature = float(data["temperature"])
        humidity = float(data["humidity"])
        rainfall = float(data["rainfall"])
        forecast_rain_mm = float(data.get("forecastRain") or 0.0)
    except (TypeError, ValueError):
        return jsonify({
            "status": "error",
            "message": "Soil moisture, temperature, humidity, and rainfall must be numeric values."
        }), 400

    # Range Validations
    if soil_moisture is not None and not (0 <= soil_moisture <= 100):
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

    if forecast_rain_mm < 0:
        forecast_rain_mm = 0.0

    # 3. Agronomic Decision Engine
    crop_profile = _get_crop_profile(crop_name)
    soil_profile = _get_soil_profile(soil_type_input)
    stage_profile = _get_stage_profile(growth_stage_input)

    # Base thresholds
    base_min = crop_profile["min_optimal"]
    base_max = crop_profile["max_optimal"]
    base_crit = crop_profile["critical_threshold"]

    # Stage and soil adjustments
    stage_boost = stage_profile["threshold_boost"]
    soil_adj = soil_profile["threshold_adj"]

    effective_min = max(20.0, min(90.0, base_min + stage_boost + soil_adj))
    effective_max = max(effective_min + 10.0, min(95.0, base_max + stage_boost + soil_adj))
    effective_crit = max(15.0, min(effective_min - 5.0, base_crit + stage_boost))

    # Multipliers for application depth
    soil_factor = soil_profile["factor"]
    stage_factor = stage_profile["depth_factor"]

    # Timing Recommendation
    if forecast_rain_mm >= 5.0:
        suggested_time = f"Deferred — Expected Rainfall ({forecast_rain_mm:.1f} mm within 24–48h)"
        timing_reason = (
            f"Precipitation of {forecast_rain_mm:.1f} mm is forecast in the next 24 to 48 hours. "
            "Hold irrigation to take advantage of natural rain and prevent nutrient leaching."
        )
    elif temperature >= 33.0:
        suggested_time = "Early Morning (5:30 AM – 8:00 AM) or Late Evening (5:30 PM – 7:30 PM)"
        timing_reason = (
            f"Under hot weather ({temperature:.1f}°C), irrigating during the cooler morning or evening "
            "avoids 25%–40% evaporative losses and prevents leaf scalding."
        )
    elif temperature <= 18.0:
        suggested_time = "Mid-Morning (9:00 AM – 11:30 AM)"
        timing_reason = (
            f"Under cool conditions ({temperature:.1f}°C), morning watering allows the plant canopy to dry "
            "before cold nightfall, minimizing fungal pathogens."
        )
    else:
        suggested_time = "Morning (6:30 AM – 9:00 AM) or Evening (5:00 PM – 7:00 PM)"
        timing_reason = "Standard calm hours minimize wind drift and evaporative loss."

    # Weather advisories
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

    if forecast_rain_mm >= 5:
        weather_advisories.append(
            f"🌧️ Forecast Alert: {forecast_rain_mm:.1f} mm rain expected in next 24–48 hours."
        )

    weather_advisory_text = (
        " ".join(weather_advisories)
        if weather_advisories
        else "Weather conditions are within normal seasonal range for crop growth."
    )

    # Core Decision Logic
    water_saved_mm = 0.0

    # CASE 1: Unmeasured Soil Moisture (Graceful Fallback without fabricating data)
    if soil_moisture is None:
        status = "Guidance (Unmeasured)"
        is_needed = False
        amount_mm = 0.0
        explanation = (
            f"Soil moisture was not measured. For {crop_name} in the {stage_profile['display_name']} stage "
            f"grown in {soil_profile['display_name']} under current weather ({temperature:.1f}°C, {humidity:.1f}% RH), "
            f"here is stage-specific agronomic guidance. Inspect root-zone soil before turning on irrigation pumps."
        )
        next_steps = [
            "Perform a tactile check: Dig 15–20 cm into root depth and squeeze soil in your hand.",
            f"If soil feels dry and crumbly, apply ~{round(20.0 * soil_factor * stage_factor, 1)} mm depth during {suggested_time}.",
            f"For {crop_name} in {stage_profile['display_name']}, {stage_profile['advice']}",
            "Connect an IoT soil moisture sensor or use a tensiometer to receive automated quantitative scheduling."
        ]

    # CASE 2: Upcoming Rain Forecast Deferral (Save Water!)
    elif forecast_rain_mm >= 5.0 and soil_moisture > effective_crit:
        status = "Postpone / Rain Expected"
        is_needed = False
        potential_mm = round(max(15.0, (effective_min - soil_moisture) * 0.8 * soil_factor * stage_factor), 1)
        water_saved_mm = potential_mm
        amount_mm = 0.0
        litres_saved_ha = int(water_saved_mm * 10000)
        explanation = (
            f"Upcoming rainfall of {forecast_rain_mm:.1f} mm is forecast within the next 24 to 48 hours. "
            f"Soil moisture ({soil_moisture:.1f}%) is currently above critical threshold ({effective_crit:.1f}%). "
            f"Postponing irrigation saves approximately {water_saved_mm:.1f} mm ({litres_saved_ha:,} Litres/hectare) "
            "and prevents waterlogging and nutrient leaching."
        )
        next_steps = [
            f"Postpone scheduled irrigation to utilize the upcoming {forecast_rain_mm:.1f} mm rainfall.",
            "Verify that field furrows and drainage outlets are unobstructed.",
            "Re-check soil moisture 24 hours after rainfall before resuming irrigation."
        ]

    # CASE 3: Overwatered
    elif soil_moisture > effective_max + 8 or (soil_moisture > effective_max and rainfall >= 15):
        status = "Overwatered"
        is_needed = False
        amount_mm = 0.0
        explanation = (
            f"Soil moisture ({soil_moisture:.1f}%) exceeds the optimal ceiling ({effective_max:.1f}%) for {crop_name}. "
            "Excess moisture can restrict root respiration and promote root diseases."
        )
        next_steps = [
            "Ensure field surface drainage is clear to prevent standing water pools.",
            "Pause all irrigation until soil dries down into the optimal range.",
            "Scout for signs of root rot or leaf yellowing caused by waterlogging."
        ]

    # CASE 4: Adequate
    elif soil_moisture >= effective_min:
        status = "Adequate"
        is_needed = False
        amount_mm = 0.0
        explanation = (
            f"Soil moisture ({soil_moisture:.1f}%) is within the optimal range ({effective_min:.1f}–{effective_max:.1f}%) for {crop_name}. "
            "Current soil water reserves are sufficient for healthy plant development."
        )
        next_steps = [
            "No irrigation is required at this time.",
            "Re-check soil moisture in 2 to 3 days or following hot, windy weather.",
            "Inspect mulch or ground cover to preserve existing soil moisture."
        ]

    # CASE 5: Recommended (Moderate Deficit)
    elif soil_moisture > effective_crit:
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
            raw_depth = (effective_min - soil_moisture) * 0.8 * soil_factor * stage_factor
            amount_mm = round(max(15.0, raw_depth), 1)
            explanation = (
                f"Soil moisture ({soil_moisture:.1f}%) has fallen below the optimal threshold ({effective_min:.1f}%) for {crop_name} "
                f"in {soil_profile['display_name']} at {stage_profile['display_name']}. "
                "Applying irrigation within the next 24 to 48 hours is recommended to avoid moisture stress."
            )
            next_steps = [
                f"Schedule irrigation during {suggested_time} to minimize evaporative loss.",
                f"{soil_profile['advice']}",
                "Deliver water uniformly around the crop root zone.",
                "Verify moisture penetration with a soil probe 2 hours after watering."
            ]

    # CASE 6: Urgent (Critical Deficit)
    else:
        status = "Urgent"
        is_needed = True
        raw_depth = (effective_min - soil_moisture) * 1.0 * soil_factor * stage_factor
        amount_mm = round(max(25.0, raw_depth), 1)
        critical_alert = " ⚠️ FLOWERING STAGE ALERT: Moisture deficit during bloom will cause flower abortion!" if stage_profile["critical"] else ""
        explanation = (
            f"Critical water deficit detected! Soil moisture ({soil_moisture:.1f}%) is at or below the critical "
            f"threshold ({effective_crit:.1f}%) for {crop_name}. Immediate irrigation is needed to prevent wilting and yield damage.{critical_alert}"
        )
        next_steps = [
            "Irrigate immediately without delay.",
            f"Ensure water penetrates to active root depth (~{int(30 * stage_factor)}–{int(50 * stage_factor)} cm).",
            f"{soil_profile['advice']}",
            "Avoid heavy chemical fertilizer applications until soil moisture is restored."
        ]

    # Format Water Quantity
    if amount_mm > 0:
        litres_per_ha = int(amount_mm * 10000)
        litres_per_acre = int(amount_mm * 4047)
        water_quantity_display = f"~{amount_mm} mm depth ({litres_per_ha:,} L/ha • {litres_per_acre:,} L/acre)"
    elif water_saved_mm > 0:
        water_quantity_display = f"0 mm (Saved ~{water_saved_mm} mm / {int(water_saved_mm * 10000):,} L/ha by deferring for rain)"
    elif soil_moisture is None:
        water_quantity_display = "Unmeasured (Tactile test required)"
    else:
        water_quantity_display = "0 mm depth (No additional water required)"

    # Water Saving Conservation Tips
    water_saving_tips = [
        soil_profile["tips"][0],
        stage_profile["tips"][0],
        f"Irrigation Timing: {suggested_time} saves up to 35% water vs midday sunshine.",
        "Consider organic mulching (straw/crop residue) to reduce soil surface evaporation by 20–30%."
    ]

    recommendation = {
        "status": status,
        "is_irrigation_needed": is_needed,
        "suggested_time": suggested_time,
        "timing_reason": timing_reason,
        "water_saved_mm": water_saved_mm,
        "water_saved_litres_ha": int(water_saved_mm * 10000),
        "water_quantity": {
            "amount_mm": amount_mm,
            "display": water_quantity_display,
            "units": "mm depth (1 mm = 10,000 Litres/hectare ≈ 4,047 Litres/acre)",
            "assumptions": (
                f"Calculated for {crop_name} in {soil_profile['display_name']} at {stage_profile['display_name']} stage. "
                "Actual duration depends on field pump discharge rate, drip emitter spacing, and slope."
            ),
        },
        "duration_info": {
            "duration_hours": None,
            "formula": "Duration (hours) = Required Volume (Litres) / System Discharge Rate (Litres/hour).",
            "explanation": (
                "Irrigation duration cannot be calculated without your field's specific pump/flow rate "
                "(e.g., pump discharge in L/sec or drip emitter rate in L/h). "
                "Formula: Duration (hours) = Required Volume (Litres) / System Discharge Rate (Litres/hour)."
            ),
        },
        "explanation": explanation,
        "weather_advisory": weather_advisory_text,
        "next_steps": next_steps,
        "water_saving_tips": water_saving_tips,
        "soil_info": {
            "soil_type": soil_profile["key"],
            "display_name": soil_profile["display_name"],
            "retention": soil_profile["retention"],
            "infiltration": soil_profile["infiltration"],
            "factor": soil_profile["factor"]
        },
        "stage_info": {
            "growth_stage": stage_profile["key"],
            "display_name": stage_profile["display_name"],
            "critical_stage": stage_profile["critical"],
            "depth_factor": stage_profile["depth_factor"]
        },
        "crop_info": {
            "crop": crop_name,
            "profile_name": crop_profile["display_name"],
            "optimal_range": f"{effective_min:.0f}% – {effective_max:.0f}%",
            "base_optimal_range": f"{base_min}% – {base_max}%",
            "water_sensitivity": crop_profile["water_sensitivity"],
            "notes": crop_profile["notes"],
        },
    }

    # 4. Authenticated Persistence (Save to irrigation_history)
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
                         recommendation_status, is_irrigation_needed, water_quantity_mm, notes,
                         soil_type, growth_stage, timing_recommendation, water_saved_mm, forecast_rain_mm)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                        soil_profile["key"],
                        stage_profile["key"],
                        suggested_time,
                        water_saved_mm,
                        forecast_rain_mm
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
            "soilType": soil_profile["key"],
            "growthStage": stage_profile["key"],
            "temperature": temperature,
            "humidity": humidity,
            "rainfall": rainfall,
            "forecastRain": forecast_rain_mm,
            "location": location,
            "weatherAutoFetched": weather_auto_fetched
        },
        "history_saved": history_saved,
    }), 200


# =============================================================================
# IRRIGATION HISTORY ENDPOINT
# =============================================================================

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
                   recommendation_status, is_irrigation_needed, water_quantity_mm, notes,
                   soil_type, growth_stage, timing_recommendation, water_saved_mm, forecast_rain_mm,
                   created_at
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
                "soil_moisture": float(r["soil_moisture"]) if r.get("soil_moisture") is not None else None,
                "temperature": float(r["temperature"]),
                "humidity": float(r["humidity"]),
                "rainfall": float(r["rainfall"]),
                "location": r.get("location"),
                "recommendation_status": r["recommendation_status"],
                "is_irrigation_needed": bool(r["is_irrigation_needed"]),
                "water_quantity_mm": float(r["water_quantity_mm"]) if r.get("water_quantity_mm") is not None else 0.0,
                "notes": r.get("notes"),
                "soil_type": r.get("soil_type") or "loamy",
                "growth_stage": r.get("growth_stage") or "vegetative",
                "timing_recommendation": r.get("timing_recommendation") or "Morning or Evening",
                "water_saved_mm": float(r.get("water_saved_mm") or 0.0),
                "forecast_rain_mm": float(r.get("forecast_rain_mm") or 0.0),
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


@irrigation_bp.route("/history/<int:record_id>", methods=["DELETE"])
def delete_irrigation_history(record_id):
    """Delete a specific irrigation history record belonging to the authenticated user."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"status": "error", "message": "Authentication required."}), 401

    token = auth_header[len("Bearer "):].strip()
    user_id = get_user_id_from_token(token)
    if user_id is None:
        return jsonify({"status": "error", "message": "Invalid session."}), 401

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM irrigation_history WHERE id = %s AND user_id = %s", (record_id, user_id))
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"status": "error", "message": "Record not found or unauthorized."}), 404
        return jsonify({"status": "success", "message": "Record deleted successfully."}), 200
    except Exception as err:
        print(f"Delete irrigation record error: {err}")
        return jsonify({"status": "error", "message": "Failed to delete record."}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =============================================================================
# STATS & SUMMARY ENDPOINT
# =============================================================================

@irrigation_bp.route("/stats", methods=["GET"])
def get_irrigation_stats():
    """Return aggregated irrigation statistics for the authenticated user."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"status": "error", "message": "Authentication required."}), 401

    token = auth_header[len("Bearer "):].strip()
    user_id = get_user_id_from_token(token)
    if user_id is None:
        return jsonify({"status": "error", "message": "Invalid session."}), 401

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT
                COUNT(*) as total_checks,
                SUM(CASE WHEN is_irrigation_needed = 1 THEN 1 ELSE 0 END) as needed_count,
                SUM(CASE WHEN recommendation_status = 'Urgent' THEN 1 ELSE 0 END) as urgent_count,
                SUM(CASE WHEN recommendation_status LIKE 'Postpone%' THEN 1 ELSE 0 END) as postponed_count,
                SUM(COALESCE(water_saved_mm, 0.0)) as total_water_saved_mm
            FROM irrigation_history
            WHERE user_id = %s
            """,
            (user_id,),
        )
        stats = cur.fetchone() or {}
        total_saved_mm = float(stats.get("total_water_saved_mm") or 0.0)
        total_saved_litres = int(total_saved_mm * 10000)

        return jsonify({
            "status": "success",
            "stats": {
                "total_checks": int(stats.get("total_checks") or 0),
                "needed_count": int(stats.get("needed_count") or 0),
                "urgent_count": int(stats.get("urgent_count") or 0),
                "postponed_count": int(stats.get("postponed_count") or 0),
                "total_water_saved_mm": round(total_saved_mm, 1),
                "total_water_saved_litres": total_saved_litres
            }
        }), 200
    except Exception as err:
        print(f"Irrigation stats error: {err}")
        return jsonify({"status": "error", "message": "Failed to calculate stats."}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =============================================================================
# CONTEXT CROPS & SOILS CATALOG ENDPOINT
# =============================================================================

@irrigation_bp.route("/context-crops", methods=["GET"])
def get_context_crops():
    """Return user's registered crops (if authenticated) alongside standard catalogs."""
    user_crops = []
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):].strip()
        user_id = get_user_id_from_token(token)
        if user_id is not None:
            conn = None
            cur = None
            try:
                conn = get_db_connection()
                cur = conn.cursor(dictionary=True)
                cur.execute(
                    """
                    SELECT c.id, c.crop_name, c.variety, c.growth_status, c.planting_date,
                           f.farm_name, f.location
                    FROM crops c
                    LEFT JOIN farms f ON c.farm_id = f.id
                    WHERE c.user_id = %s
                    ORDER BY c.created_at DESC
                    LIMIT 20
                    """,
                    (user_id,)
                )
                rows = cur.fetchall()
                for r in rows:
                    user_crops.append({
                        "id": r["id"],
                        "crop_name": r["crop_name"],
                        "variety": r.get("variety"),
                        "growth_status": r.get("growth_status"),
                        "farm_name": r.get("farm_name"),
                        "location": r.get("location")
                    })
            except Exception as e:
                print(f"Error fetching user crops for irrigation context: {e}")
            finally:
                if cur:
                    cur.close()
                if conn:
                    conn.close()

    return jsonify({
        "status": "success",
        "user_crops": user_crops,
        "standard_crops": [
            {"key": k, "display_name": v["display_name"], "sensitivity": v["water_sensitivity"]}
            for k, v in CROP_PROFILES.items()
        ],
        "soil_types": [
            {"key": k, "display_name": v["display_name"], "retention": v["retention"]}
            for k, v in SOIL_PROFILES.items()
        ],
        "growth_stages": [
            {"key": k, "display_name": v["display_name"], "critical": v["critical"]}
            for k, v in GROWTH_STAGES.items()
        ]
    }), 200


# =============================================================================
# WEATHER PREVIEW / AUTO-FILL ENDPOINT
# =============================================================================

@irrigation_bp.route("/weather-preview", methods=["GET"])
def weather_preview():
    """Fetch live temperature, humidity, rainfall, and 24-48h forecast rain for 1-click auto-fill."""
    location = request.args.get("location", "").strip()
    if not location:
        return jsonify({"status": "error", "message": "Location parameter is required."}), 400

    weather = _fetch_live_weather(location)
    if not weather:
        return jsonify({
            "status": "error",
            "message": "Unable to fetch live weather for the specified location."
        }), 502

    return jsonify({
        "status": "success",
        "weather": weather
    }), 200
