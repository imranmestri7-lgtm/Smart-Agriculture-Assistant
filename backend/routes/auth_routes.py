from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from twilio.rest import Client
import os

from config import get_db_connection

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# --------------------------------------------------
# TWILIO CONFIGURATION
# --------------------------------------------------
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_VERIFY_SERVICE_SID = os.getenv("TWILIO_VERIFY_SERVICE_SID")


def get_twilio_client():
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        raise Exception("Twilio credentials are not configured")

    return Client(
        TWILIO_ACCOUNT_SID,
        TWILIO_AUTH_TOKEN
    )


# --------------------------------------------------
# HELPER
# --------------------------------------------------
def normalize_mobile(mobile):
    mobile = str(mobile or "").strip()

    mobile = mobile.replace(" ", "")
    mobile = mobile.replace("-", "")

    if mobile.startswith("+91"):
        mobile = mobile[3:]

    elif mobile.startswith("91") and len(mobile) == 12:
        mobile = mobile[2:]

    return mobile


def mobile_to_e164(mobile):
    return f"+91{mobile}"


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

        full_name = str(
            data.get("full_name", "")
        ).strip()

        auth_method = str(
            data.get("auth_method", "")
        ).strip().lower()

        preferred_language = str(
            data.get("preferred_language", "English")
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

            if (
                not mobile_number.isdigit()
                or len(mobile_number) != 10
            ):
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
        email = str(
            data.get("email", "")
        ).strip().lower()

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

        email = str(
            data.get("email", "")
        ).strip().lower()

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
# SEND OTP USING TWILIO VERIFY
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

        if (
            not mobile_number.isdigit()
            or len(mobile_number) != 10
        ):
            return jsonify({
                "status": "error",
                "message": "Please enter a valid 10-digit mobile number"
            }), 400

        # --------------------------------------------------
        # CHECK USER
        # --------------------------------------------------
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

        # --------------------------------------------------
        # CHECK TWILIO CONFIGURATION
        # --------------------------------------------------
        if not TWILIO_VERIFY_SERVICE_SID:
            return jsonify({
                "status": "error",
                "message": "Twilio Verify Service is not configured"
            }), 500

        # --------------------------------------------------
        # SEND SMS THROUGH TWILIO VERIFY
        # --------------------------------------------------
        twilio_client = get_twilio_client()

        verification = (
            twilio_client
            .verify
            .v2
            .services(TWILIO_VERIFY_SERVICE_SID)
            .verifications
            .create(
                to=mobile_to_e164(mobile_number),
                channel="sms"
            )
        )

        return jsonify({
            "status": "success",
            "message": "OTP sent successfully",
            "verification_status": verification.status,
            "expires_in": 600
        }), 200

    except Exception as error:

        if connection:
            connection.rollback()

        print("Twilio Send OTP Error:", str(error))

        return jsonify({
            "status": "error",
            "message": "Unable to send OTP. Please try again."
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# --------------------------------------------------
# VERIFY OTP USING TWILIO VERIFY
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

        if (
            not mobile_number.isdigit()
            or len(mobile_number) != 10
        ):
            return jsonify({
                "status": "error",
                "message": "Invalid mobile number"
            }), 400

        if len(otp) != 6 or not otp.isdigit():
            return jsonify({
                "status": "error",
                "message": "OTP must contain 6 digits"
            }), 400

        if not TWILIO_VERIFY_SERVICE_SID:
            return jsonify({
                "status": "error",
                "message": "Twilio Verify Service is not configured"
            }), 500

        # --------------------------------------------------
        # VERIFY OTP WITH TWILIO
        # --------------------------------------------------
        twilio_client = get_twilio_client()

        verification_check = (
            twilio_client
            .verify
            .v2
            .services(TWILIO_VERIFY_SERVICE_SID)
            .verification_checks
            .create(
                to=mobile_to_e164(mobile_number),
                code=otp
            )
        )

        if verification_check.status != "approved":
            return jsonify({
                "status": "error",
                "message": "Invalid or expired OTP"
            }), 401

        # --------------------------------------------------
        # GET USER
        # --------------------------------------------------
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
                "message": "User not found"
            }), 404

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

        print("Twilio Verify OTP Error:", str(error))

        return jsonify({
            "status": "error",
            "message": "OTP verification failed. Please try again."
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()