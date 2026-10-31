try:
    import mysql.connector
except ImportError:
    class _DummyMySQL:
        class Error(Exception):
            pass
    mysql = _DummyMySQL()
import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from config import get_db_connection
from routes.auth_routes import auth_bp
from routes.chat_routes import chat_bp
from routes.disease_routes import disease_bp
from routes.weather_routes import weather_bp
from routes.crop_routes import crop_bp
from routes.irrigation_routes import irrigation_bp
from routes.farm_crop_routes import farm_bp, crop_mgmt_bp
from routes.analytics_routes import analytics_bp
from routes.notification_routes import notification_bp
from routes.iot_routes import iot_bp

app = Flask(__name__)

CORS(app)

# Register authentication routes
app.register_blueprint(auth_bp)
app.register_blueprint(chat_bp)

# Register crop disease prediction and irrigation routes
app.register_blueprint(disease_bp)
app.register_blueprint(irrigation_bp)

# Register weather routes
app.register_blueprint(weather_bp)

# Register crop recommendation routes
app.register_blueprint(crop_bp)

# Register farm and crop management routes
app.register_blueprint(farm_bp)
app.register_blueprint(crop_mgmt_bp)

# Register smart analytics routes
app.register_blueprint(analytics_bp)

# Register smart notifications and alerts routes
app.register_blueprint(notification_bp)

# Register IoT smart farm monitoring routes
app.register_blueprint(iot_bp)

@app.route("/")
def home():
    return jsonify({
        "message": "Smart Agriculture Assistant Backend is running!"
    })


@app.route("/api/test")
def test():
    return jsonify({
        "status": "success",
        "message": "API connection successful"
    })


@app.route("/api/db-test")
def db_test():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE()")

        result = cursor.fetchone()

        return jsonify({
            "status": "success",
            "database": result[0]
        })

    except mysql.connector.Error as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@app.route("/<path:filename>")
def serve_frontend(filename):
    safe_path = os.path.join(PROJECT_ROOT, filename)
    if os.path.isfile(safe_path):
        return send_from_directory(PROJECT_ROOT, filename)
    return jsonify({"status": "error", "message": "File not found"}), 404


if __name__ == "__main__":
    app.run(debug=True, port=5000)