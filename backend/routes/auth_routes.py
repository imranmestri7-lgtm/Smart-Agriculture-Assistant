from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash

from config import get_db_connection

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# --------------------------------------------------
# REGISTER
# --------------------------------------------------
@auth_bp.route("/register", methods=["POST"])
def register():
    connection = None
    cursor = None

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "status": "error",
                "message": "Request body is required"
            }), 400

        full_name = data.get("full_name", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        if not full_name or not email or not password:
            return jsonify({
                "status": "error",
                "message": "Full name, email and password are required"
            }), 400

        if len(password) < 6:
            return jsonify({
                "status": "error",
                "message": "Password must contain at least 6 characters"
            }), 400

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT id FROM users WHERE email = %s",
            (email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:
            return jsonify({
                "status": "error",
                "message": "Email is already registered"
            }), 409

        password_hash = generate_password_hash(password)

        cursor.execute(
            """
            INSERT INTO users
            (full_name, email, password_hash)
            VALUES (%s, %s, %s)
            """,
            (full_name, email, password_hash)
        )

        connection.commit()

        user_id = cursor.lastrowid

        return jsonify({
            "status": "success",
            "message": "Registration successful",
            "user": {
                "id": user_id,
                "full_name": full_name,
                "email": email
            }
        }), 201

    except Exception as error:

        if connection:
            connection.rollback()

        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# --------------------------------------------------
# LOGIN
# --------------------------------------------------
@auth_bp.route("/login", methods=["POST"])
def login():
    connection = None
    cursor = None

    try:
        data = request.get_json()

        if not data:
            return jsonify({
                "status": "error",
                "message": "Request body is required"
            }), 400

        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        if not email or not password:
            return jsonify({
                "status": "error",
                "message": "Email and password are required"
            }), 400

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                full_name,
                email,
                password_hash,
                preferred_language
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        user = cursor.fetchone()

        if not user:
            return jsonify({
                "status": "error",
                "message": "Invalid email or password"
            }), 401

        password_is_correct = check_password_hash(
            user["password_hash"],
            password
        )

        if not password_is_correct:
            return jsonify({
                "status": "error",
                "message": "Invalid email or password"
            }), 401

        return jsonify({
            "status": "success",
            "message": "Login successful",
            "user": {
                "id": user["id"],
                "full_name": user["full_name"],
                "email": user["email"],
                "preferred_language": user["preferred_language"]
            }
        }), 200

    except Exception as error:

        return jsonify({
            "status": "error",
            "message": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()