from flask import Blueprint, request, jsonify

irrigation_bp = Blueprint('irrigation', __name__, url_prefix='/api/irrigation')

@irrigation_bp.route('/recommend', methods=['POST'])
def recommend_irrigation():
    """Simple rule‑based irrigation recommendation.
    Expects JSON with fields:
        crop (optional), soilMoisture, temperature, humidity, rainfall
    Returns a recommendation string.
    """
    data = request.get_json(silent=True) or {}
    # Basic validation
    required = ['soilMoisture', 'temperature', 'humidity', 'rainfall']
    missing = [k for k in required if k not in data]
    if missing:
        return jsonify({
            'status': 'error',
            'message': f"Missing required fields: {', '.join(missing)}"
        }), 400
    try:
        sm = float(data.get('soilMoisture', 0))
        temp = float(data.get('temperature', 0))
        hum = float(data.get('humidity', 0))
        rain = float(data.get('rainfall', 0))
    except (TypeError, ValueError):
        return jsonify({
            'status': 'error',
            'message': 'All numeric fields must be numbers.'
        }), 400

    # Very naive rule: if soil moisture low and rainfall low => need irrigation
    if sm < 30 and rain < 5:
        rec = 'Irrigate now – soil is dry and recent rainfall is minimal.'
    else:
        rec = 'No immediate irrigation needed – soil moisture is sufficient.'
    return jsonify({
        'status': 'success',
        'recommendation': rec,
        'details': {
            'soilMoisture': sm,
            'temperature': temp,
            'humidity': hum,
            'rainfall': rain
        }
    })
