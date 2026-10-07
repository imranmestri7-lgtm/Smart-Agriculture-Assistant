from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets

from config import get_db_connection


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# --------------------------------------------------
# NORMALIZE MOBILE NUMBER
# --------------------------------------------------
def normalize_mobile(mobile):
    mobile = str(mobile).strip()

    # Remove spaces and hyphens
    mobile = mobile.replace(" ", "").replace("-", "")

    # Convert +91XXXXXXXXXX to XXXXXXXXXX
    if mobile.startswith("+91"):
        mobile = mobile[3:]

    # Convert 91XXXXXXXXXX to XXXXXXXXXX
    elif mobile.startswith("91") and len(mobile) == 12:
        mobile = mobile[2:]

    return mobile


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
        mobile_number = normalize_mobile(
            data.get("mobile_number", "")
        )
        preferred_language = data.get(
            "preferred_language",
            "English"
        ).strip()

        # Validate full name
        if not full_name:
            return jsonify({
                "status": "error",
                "message": "Full name is required"
            }), 400

        # Validate mobile number
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

        # Check whether mobile number already exists
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

        # Create new user
        cursor.execute(
            """
            INSERT INTO users
            (
                full_name,
                mobile_number,
                preferred_language
            )
            VALUES (%s, %s, %s)
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
            "message": "Registration successful",
            "user": {
                "id": user_id,
                "full_name": full_name,
                "mobile_number": mobile_number,
                "preferred_language": preferred_language
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

        # Validate mobile number
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

        # Find user
        cursor.execute(
            """
            SELECT
                id,
                full_name,
                mobile_number,
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

        # Generate 6-digit OTP
        otp = str(
            secrets.randbelow(900000) + 100000
        )

        # Hash OTP before storing it
        otp_hash = generate_password_hash(otp)

        # OTP valid for 5 minutes
        otp_expires_at = datetime.now() + timedelta(minutes=5)

        # Save OTP
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

        # DEVELOPMENT ONLY
        # Later this OTP will be sent through SMS.
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

        # Validate mobile number
        if not mobile_number:
            return jsonify({
                "status": "error",
                "message": "Mobile number is required"
            }), 400

        if not mobile_number.isdigit() or len(mobile_number) != 10:
            return jsonify({
                "status": "error",
                "message": "Invalid mobile number"
            }), 400

        # Validate OTP
        if not otp:
            return jsonify({
                "status": "error",
                "message": "OTP is required"
            }), 400

        if len(otp) != 6 or not otp.isdigit():
            return jsonify({
                "status": "error",
                "message": "OTP must contain 6 digits"
            }), 400

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Find user
        cursor.execute(
            """
            SELECT
                id,
                full_name,
                mobile_number,
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

        # Check whether OTP exists
        if not user["otp_hash"]:
            return jsonify({
                "status": "error",
                "message": "Please request a new OTP"
            }), 400

        # Check OTP expiry
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

        # Check OTP
        otp_is_correct = check_password_hash(
            user["otp_hash"],
            otp
        )

        if not otp_is_correct:
            return jsonify({
                "status": "error",
                "message": "Invalid OTP"
            }), 401

        # OTP successfully verified
        # Remove OTP so it cannot be reused
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
                "preferred_language": user["preferred_language"]
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