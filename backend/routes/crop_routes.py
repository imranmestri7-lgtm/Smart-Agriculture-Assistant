from flask import Blueprint, request, jsonify
from utils.auth_tokens import get_user_id_from_token
from utils.seasonal_crop_advisor import generate_seasonal_crop_recommendations

crop_bp = Blueprint('crop', __name__, url_prefix='/api/crop')


def _authenticate():
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
            "message": "Invalid or expired token. Please log in again."
        }), 401)
    return user_id, None


@crop_bp.route('/recommendations', methods=['GET'])
def get_seasonal_recommendations():
    """Retrieve seasonal and soil-aware crop recommendations."""
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


@crop_bp.route('/recommend', methods=['POST'])
def recommend_crop():
    """Very simple rule‑based crop recommendation.
    Expects a JSON payload with numeric fields:
        nitrogen, phosphorus, potassium, ph, temperature, humidity, rainfall
    Returns a JSON with a `recommendation` string.
    """
    data = request.get_json(silent=True) or {}
    # Basic validation – ensure required keys are present and numeric
    required = ['nitrogen', 'phosphorus', 'potassium']
    missing = [k for k in required if k not in data]
    if missing:
        return jsonify({
            'status': 'error',
            'message': f'Missing required fields: {", ".join(missing)}'
        }), 400
    try:
        n = float(data.get('nitrogen', 0))
        p = float(data.get('phosphorus', 0))
        k = float(data.get('potassium', 0))
    except (TypeError, ValueError):
        return jsonify({
            'status': 'error',
            'message': 'Nutrient values must be numbers.'
        }), 400

    # Very naive rule: choose a crop based on nutrient richness
    if n > 80 and p > 80 and k > 80:
        rec = 'Rice'
    elif n < 40 and p < 40 and k < 40:
        rec = 'Wheat'
    else:
        rec = 'Maize'
    return jsonify({
        'status': 'success',
        'recommendation': rec,
        'details': {
            'nitrogen': n,
            'phosphorus': p,
            'potassium': k
        }
    })
