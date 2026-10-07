from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets

from config import get_db_connection

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# --------------------------------------------------
# HELPER
# --------------------------------------------------
def normalize_mobile(mobile):
    mobile = str(mobile or "").strip()
    mobile = mobile.replace(" ", "").replace("-", "")

    if mobile.startswith("+91"):
        mobile = mobile[3:]
    elif mobile.startswith("91") and len(mobile) == 12:
        mobile = mobile[2:]

    return mobile


# --------------------------------------------------
# REGISTER
# Supports:
# 1. Phone registration
# 2. Email registration
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
        auth_method = data.get("auth_method", "").strip().lower()
        preferred_language = data.get(
            "preferred_language",
            "English"
        ).strip()

        if not full_name:
            return jsonify({
                "status": "error",
                "message": "Full name is required"
            }), 400

        if auth_method not in ["phone", "email"]:
            return jsonify({
                "status": "error",
                "message": "Please select phone or email registration"
            }), 400

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # --------------------------------------------------
        # PHONE REGISTRATION
        # --------------------------------------------------
        if auth_method == "phone":

            mobile_number = normalize_mobile(
                data.get("mobile_number", "")
            )

            if not mobile_number:
                return jsonify({
                    "status": "error",
                    "message": "Mobile number is required"
                }), 400

            if not mobile_number.isdigit() or len(mobile_number) != 10:
                return jsonify({
                    "status": "error",
                    "message": "Please enter a valid 10-digit mobile number"
                }), 400

            cursor.execute(
                """
                SELECT id
                FROM users
                WHERE mobile_number = %s
                """,
                (mobile_number,)
            )

            existing_user = cursor.fetchone()

            if existing_user:
                return jsonify({
                    "status": "error",
                    "message": "Mobile number is already registered"
                }), 409

            cursor.execute(
                """
                INSERT INTO users
                (
                    full_name,
                    mobile_number,
                    email,
                    password_hash,
                    preferred_language
                )
                VALUES (%s, %s, NULL, NULL, %s)
                """,
                (
                    full_name,
                    mobile_number,
                    preferred_language
                )
            )

            connection.commit()

            user_id = cursor.lastrowid

            return jsonify({
                "status": "success",
                "message": "Phone registration successful",
                "user": {
                    "id": user_id,
                    "full_name": full_name,
                    "mobile_number": mobile_number,
                    "email": None,
                    "preferred_language": preferred_language,
                    "auth_method": "phone"
                }
            }), 201

        # --------------------------------------------------
        # EMAIL REGISTRATION
        # --------------------------------------------------
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        confirm_password = data.get("confirm_password", "")

        if not email:
            return jsonify({
                "status": "error",
                "message": "Email is required"
            }), 400

        if not password:
            return jsonify({
                "status": "error",
                "message": "Password is required"
            }), 400

        if len(password) < 6:
            return jsonify({
                "status": "error",
                "message": "Password must contain at least 6 characters"
            }), 400

        if password != confirm_password:
            return jsonify({
                "status": "error",
                "message": "Passwords do not match"
            }), 400

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE email = %s
            """,
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
            (
                full_name,
                mobile_number,
                email,
                password_hash,
                preferred_language
            )
            VALUES (%s, NULL, %s, %s, %s)
            """,
            (
                full_name,
                email,
                password_hash,
                preferred_language
            )
        )

        connection.commit()

        user_id = cursor.lastrowid

        return jsonify({
            "status": "success",
            "message": "Email registration successful",
            "user": {
                "id": user_id,
                "full_name": full_name,
                "mobile_number": None,
                "email": email,
                "preferred_language": preferred_language,
                "auth_method": "email"
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
# EMAIL LOGIN
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
                mobile_number,
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

        if not user["password_hash"]:
            return jsonify({
                "status": "error",
                "message": "This account uses mobile OTP login"
            }), 400

        if not check_password_hash(
            user["password_hash"],
            password
        ):
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
                "mobile_number": user["mobile_number"],
                "email": user["email"],
                "preferred_language": user["preferred_language"],
                "auth_method": "email"
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


# --------------------------------------------------
# SEND OTP
# --------------------------------------------------
@auth_bp.route("/send-otp", methods=["POST"])
def send_otp():

    connection = None
    cursor = None

    try:

        data = request.get_json()

        if not data:
            return jsonify({
                "status": "error",
                "message": "Request body is required"
            }), 400

        mobile_number = normalize_mobile(
            data.get("mobile_number", "")
        )

        if not mobile_number:
            return jsonify({
                "status": "error",
                "message": "Mobile number is required"
            }), 400

        if not mobile_number.isdigit() or len(mobile_number) != 10:
            return jsonify({
                "status": "error",
                "message": "Please enter a valid 10-digit mobile number"
            }), 400

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                full_name,
                mobile_number,
                email,
                preferred_language
            FROM users
            WHERE mobile_number = %s
            """,
            (mobile_number,)
        )

        user = cursor.fetchone()

        if not user:
            return jsonify({
                "status": "error",
                "message": "No account found with this mobile number"
            }), 404

        otp = str(secrets.randbelow(900000) + 100000)

        otp_hash = generate_password_hash(otp)

        otp_expires_at = (
            datetime.now() + timedelta(minutes=5)
        )

        cursor.execute(
            """
            UPDATE users
            SET
                otp_hash = %s,
                otp_expires_at = %s
            WHERE id = %s
            """,
            (
                otp_hash,
                otp_expires_at,
                user["id"]
            )
        )

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "OTP generated successfully",
            "development_otp": otp,
            "expires_in": 300
        }), 200

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
# VERIFY OTP
# --------------------------------------------------
@auth_bp.route("/verify-otp", methods=["POST"])
def verify_otp():

    connection = None
    cursor = None

    try:

        data = request.get_json()

        if not data:
            return jsonify({
                "status": "error",
                "message": "Request body is required"
            }), 400

        mobile_number = normalize_mobile(
            data.get("mobile_number", "")
        )

        otp = str(
            data.get("otp", "")
        ).strip()

        if not mobile_number or not otp:
            return jsonify({
                "status": "error",
                "message": "Mobile number and OTP are required"
            }), 400

        if not mobile_number.isdigit() or len(mobile_number) != 10:
            return jsonify({
                "status": "error",
                "message": "Invalid mobile number"
            }), 400

        if len(otp) != 6 or not otp.isdigit():
            return jsonify({
                "status": "error",
                "message": "OTP must contain 6 digits"
            }), 400

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                full_name,
                mobile_number,
                email,
                preferred_language,
                otp_hash,
                otp_expires_at
            FROM users
            WHERE mobile_number = %s
            """,
            (mobile_number,)
        )

        user = cursor.fetchone()

        if not user:
            return jsonify({
                "status": "error",
                "message": "User not found"
            }), 404

        if not user["otp_hash"]:
            return jsonify({
                "status": "error",
                "message": "Please request a new OTP"
            }), 400

        if not user["otp_expires_at"]:
            return jsonify({
                "status": "error",
                "message": "OTP has expired. Please request a new OTP"
            }), 401

        if datetime.now() > user["otp_expires_at"]:
            return jsonify({
                "status": "error",
                "message": "OTP has expired. Please request a new OTP"
            }), 401

        if not check_password_hash(
            user["otp_hash"],
            otp
        ):
            return jsonify({
                "status": "error",
                "message": "Invalid OTP"
            }), 401

        cursor.execute(
            """
            UPDATE users
            SET
                otp_hash = NULL,
                otp_expires_at = NULL
            WHERE id = %s
            """,
            (user["id"],)
        )

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "OTP verified successfully",
            "user": {
                "id": user["id"],
                "full_name": user["full_name"],
                "mobile_number": user["mobile_number"],
                "email": user["email"],
                "preferred_language": user["preferred_language"],
                "auth_method": "phone"
            }
        }), 200

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