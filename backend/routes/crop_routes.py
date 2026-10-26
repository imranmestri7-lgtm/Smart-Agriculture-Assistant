from flask import Blueprint, request, jsonify

crop_bp = Blueprint('crop', __name__, url_prefix='/api/crop')

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
