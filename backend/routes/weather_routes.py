import os
import requests
from dotenv import load_dotenv
from flask import Blueprint, jsonify, request

weather_bp = Blueprint("weather", __name__, url_prefix="/api/weather")

WEATHER_API_BASE_URL = "https://api.weatherapi.com/v1"

# Ensure backend/.env is loaded
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def get_weather_api_key():
    return os.getenv("WEATHER_API_KEY", "").strip()


@weather_bp.route("/search", methods=["GET"])
def search_locations():
    """
    Search location autocomplete suggestions via server-side WeatherAPI proxy.
    Endpoint: GET /api/weather/search?q=<query>
    """
    api_key = get_weather_api_key()
    if not api_key:
        return jsonify({
            "status": "error",
            "message": "Weather service is not configured on the server."
        }), 503

    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return jsonify([]), 200

    try:
        url = f"{WEATHER_API_BASE_URL}/search.json"
        params = {
            "key": api_key,
            "q": query
        }
        response = requests.get(url, params=params, timeout=5)

        if not response.ok:
            return jsonify([]), response.status_code

        locations = response.json()

        # Preserve the existing client behavior: filter for India locations
        india_locations = [
            loc for loc in locations
            if loc.get("country") == "India"
        ]

        # Return up to 5 suggestions
        return jsonify(india_locations[:5]), 200

    except requests.exceptions.RequestException as error:
        # Avoid logging the full URL/query parameters to protect API key
        print(f"Weather search request failed: {type(error).__name__}")
        return jsonify({
            "status": "error",
            "message": "Unable to connect to weather provider."
        }), 502


@weather_bp.route("/forecast", methods=["GET"])
def get_forecast():
    """
    Retrieve current weather and 5-day forecast via server-side WeatherAPI proxy.
    Endpoint: GET /api/weather/forecast?q=<location>
    """
    api_key = get_weather_api_key()
    if not api_key:
        return jsonify({
            "status": "error",
            "message": "Weather service is not configured on the server."
        }), 503

    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({
            "status": "error",
            "message": "Location query parameter 'q' is required."
        }), 400

    days = request.args.get("days", 5)

    try:
        url = f"{WEATHER_API_BASE_URL}/forecast.json"
        params = {
            "key": api_key,
            "q": query,
            "days": days,
            "aqi": "no",
            "alerts": "no"
        }
        response = requests.get(url, params=params, timeout=8)

        # If first attempt fails (e.g. "Pune, India"), try fallback by stripping trailing country/state
        if not response.ok and "," in query:
            base_query = query.split(",")[0].strip()
            fallback_params = {
                "key": api_key,
                "q": base_query,
                "days": days,
                "aqi": "no",
                "alerts": "no"
            }
            fallback_response = requests.get(url, params=fallback_params, timeout=8)
            if fallback_response.ok:
                return jsonify(fallback_response.json()), 200

        if not response.ok:
            error_data = response.json() if response.headers.get("Content-Type", "").startswith("application/json") else {}
            return jsonify({
                "status": "error",
                "message": error_data.get("error", {}).get("message", "Weather data is not available for this location.")
            }), response.status_code

        return jsonify(response.json()), 200

    except requests.exceptions.RequestException as error:
        # Avoid logging the full URL/query parameters to protect API key
        print(f"Weather forecast request failed: {type(error).__name__}")
        return jsonify({
            "status": "error",
            "message": "Unable to connect to weather provider."
        }), 502
