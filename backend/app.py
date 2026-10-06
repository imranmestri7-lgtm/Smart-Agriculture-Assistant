import mysql.connector
from flask import Flask, jsonify
from flask_cors import CORS

from config import get_db_connection
from routes.auth_routes import auth_bp


app = Flask(__name__)

CORS(app)

# Register authentication routes
app.register_blueprint(auth_bp)


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


if __name__ == "__main__":
    app.run(debug=True, port=5000)