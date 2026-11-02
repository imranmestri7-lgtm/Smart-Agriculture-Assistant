"""Authenticated API endpoints for the AgriSmart farming assistant."""

import os
import re
from flask import Blueprint, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename
from config import get_db_connection
from utils.auth_tokens import get_user_id_from_token
from utils.chatbot import MAX_MESSAGE_LENGTH, generate_response
from utils.image_chat import (
    UPLOADS_DIR,
    analyze_leaf_image,
    get_default_prompt,
    save_chat_image,
    validate_image_file,
)

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")


def _fetch_farmer_context(user_id):
    """Retrieve authenticated farmer's context for personal assistant answers."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, farm_name, location, total_area, area_unit
            FROM farms
            WHERE user_id = %s
            ORDER BY farm_name ASC
        """, (user_id,))
        farms = cursor.fetchall() or []

        cursor.execute("""
            SELECT c.id, c.farm_id, c.crop_name, c.variety, c.planting_date, c.expected_harvest_date,
                   c.growth_status, c.cultivated_area, c.area_unit, c.notes, c.updated_at,
                   f.farm_name, f.location
            FROM crops c
            LEFT JOIN farms f ON f.id = c.farm_id
            WHERE c.user_id = %s
            ORDER BY c.created_at DESC
        """, (user_id,))
        crops = cursor.fetchall() or []

        cursor.execute("""
            SELECT predicted_class, confidence, diagnosis_date
            FROM diagnosis_history
            WHERE user_id = %s
            ORDER BY diagnosis_date DESC
            LIMIT 5
        """, (user_id,))
        diagnoses = cursor.fetchall() or []

        cursor.execute("""
            SELECT crop, soil_moisture, is_irrigation_needed, water_quantity_mm, recommendation_status, created_at
            FROM irrigation_history
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 5
        """, (user_id,))
        irrigations = cursor.fetchall() or []

        cursor.execute("""
            SELECT message, response, created_at
            FROM chat_history
            WHERE user_id = %s
            ORDER BY created_at DESC, id DESC
            LIMIT 5
        """, (user_id,))
        recent_chat = cursor.fetchall() or []

        return {
            "user_id": user_id,
            "farms": farms,
            "crops": crops,
            "recent_diagnoses": diagnoses,
            "recent_irrigations": irrigations,
            "recent_chat": list(reversed(recent_chat))
        }
    except Exception as e:
        print(f"Could not load farmer context: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@chat_bp.route("/suggestions", methods=["GET"])
def get_chat_suggestions():
    """Return multilingual quick question suggestions for Farmer Assistant."""
    lang = request.args.get("language", "en").lower()
    if lang not in ("en", "mr", "hi"):
        lang = "en"

    suggestions = {
        "en": [
            {"id": "crop_status", "label": "🌾 My crop status", "query": "What is my crop status?"},
            {"id": "irrigation_guidance", "label": "💧 Irrigation guidance", "query": "What irrigation guidance did I receive?"},
            {"id": "disease_prevention", "label": "🍃 Disease prevention", "query": "Show my recent disease diagnosis and precautions."},
            {"id": "weather_info", "label": "🌦️ Weather information", "query": "What is the weather forecast for my farm?"},
            {"id": "harvest_reminders", "label": "⏱️ Harvest reminders", "query": "Which crops are ready for harvest?"},
            {"id": "farm_summary", "label": "🏡 My farm summary", "query": "Give me a summary of my registered farms."}
        ],
        "mr": [
            {"id": "crop_status", "label": "🌾 पिकांची स्थिती", "query": "माझ्या पिकांची सद्यस्थिती काय आहे?"},
            {"id": "irrigation_guidance", "label": "💧 सिंचन मार्गदर्शन", "query": "मला कोणती सिंचन शिफारस मिळाली आहे?"},
            {"id": "disease_prevention", "label": "🍃 रोग प्रतिबंध", "query": "माझे अलीकडील रोगनिदान आणि खबरदारी दाखवा."},
            {"id": "weather_info", "label": "🌦️ हवामान माहिती", "query": "माझ्या शेतासाठी हवामान अंदाज काय आहे?"},
            {"id": "harvest_reminders", "label": "⏱️ काढणी स्मरणपत्रे", "query": "कोणती पिके काढणीसाठी तयार आहेत?"},
            {"id": "farm_summary", "label": "🏡 शेताचा सारांश", "query": "माझ्या नोंदणीकृत शेतांचा सारांश द्या."}
        ],
        "hi": [
            {"id": "crop_status", "label": "🌾 फसल की स्थिति", "query": "मेरी फसलों की वर्तमान स्थिति क्या है?"},
            {"id": "irrigation_guidance", "label": "💧 सिंचाई मार्गदर्शन", "query": "मुझे क्या सिंचाई सलाह प्राप्त हुई है?"},
            {"id": "disease_prevention", "label": "🍃 रोग रोकथाम", "query": "मेरा हालिया रोग निदान और सावधानियां दिखाएं।"},
            {"id": "weather_info", "label": "🌦️ मौसम जानकारी", "query": "मेरे खेत के लिए मौसम का पूर्वानुमान क्या है?"},
            {"id": "harvest_reminders", "label": "⏱️ कटाई रिमाइंडर", "query": "कौन सी फसलें कटाई के लिए तैयार हैं?"},
            {"id": "farm_summary", "label": "🏡 खेत का सारांश", "query": "मेरे पंजीकृत खेतों का विवरण दें।"}
        ]
    }

    return jsonify({
        "status": "success",
        "language": lang,
        "suggestions": suggestions[lang]
    }), 200


@chat_bp.route("/message", methods=["POST"])
@chat_bp.route("/image-message", methods=["POST"])
def chat_message():
    """Answer one farming question (text or image-based) from an authenticated user and persist to history."""
    authorization = request.headers.get("Authorization", "")
    scheme, separator, token = authorization.partition(" ")

    if not separator or scheme.lower() != "bearer" or not token.strip():
        return jsonify({
            "status": "error",
            "message": "Authentication required. Please log in again.",
        }), 401

    user_id = get_user_id_from_token(token.strip())
    if user_id is None:
        return jsonify({
            "status": "error",
            "message": "Your session is invalid or expired. Please log in again.",
        }), 401

    is_multipart = bool(request.content_type and "multipart/form-data" in request.content_type)
    image_file = None

    if is_multipart:
        message = (request.form.get("message") or "").strip()
        requested_language = request.form.get("language")
        if "image" in request.files:
            image_file = request.files["image"]
        elif "file" in request.files:
            image_file = request.files["file"]
    else:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({
                "status": "error",
                "message": "Send a JSON object containing a message.",
            }), 400
        message = data.get("message")
        if not isinstance(message, str):
            message = ""
        else:
            message = message.strip()
        requested_language = data.get("language")

    # Determine language
    x_language = request.headers.get("X-Language")
    if requested_language in ("en", "mr", "hi"):
        language = requested_language
    elif x_language in ("en", "mr", "hi"):
        language = x_language
    elif requested_language is None or requested_language == "auto":
        from utils.chatbot import _detect_language
        language = _detect_language(message)
        if language not in ("en", "mr", "hi"):
            language = "en"
    else:
        language = "en"

    # CASE A: IMAGE UPLOAD / CAMERA VISION
    if image_file and image_file.filename:
        # If user did not provide custom question, use sensible localized default
        if not message:
            message = get_default_prompt(language)

        if len(message) > MAX_MESSAGE_LENGTH:
            return jsonify({
                "status": "error",
                "message": f"Your message must be {MAX_MESSAGE_LENGTH} characters or fewer.",
            }), 400

        # Validate image file
        image_bytes, val_err, status_code = validate_image_file(image_file)
        if val_err:
            return jsonify({
                "status": "error",
                "message": val_err
            }), status_code

        # Save image with user isolation prefix
        safe_filename = save_chat_image(image_bytes, user_id, image_file.filename)
        image_url = f"/api/chat/image/{safe_filename}"

        # Analyze plant leaf with CNN model
        analysis = analyze_leaf_image(image_bytes, language=language)
        reply_text = analysis["reply"]

        # Persist conversation to chat_history
        db_message = f"[image:{image_url}] {message}"
        history_saved = False
        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO chat_history (user_id, message, response)
                VALUES (%s, %s, %s)
                """,
                (user_id, db_message, reply_text)
            )
            connection.commit()
            history_saved = True
        except Exception as db_err:
            print(f"Could not persist chat image message: {db_err}")
            if connection:
                try:
                    connection.rollback()
                except Exception:
                    pass
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        return jsonify({
            "status": "success",
            "reply": reply_text,
            "language": language,
            "category": "disease",
            "image_url": image_url,
            "prediction": {
                "class_name": analysis["predicted_class"],
                "confidence": analysis["confidence"],
                "is_confident": analysis["is_confident"],
                "top_predictions": analysis.get("top_predictions", [])
            },
            "knowledge": analysis["knowledge"],
            "history_saved": history_saved
        }), 200

    # CASE B: TEXT-ONLY QUESTION
    if not message:
        return jsonify({
            "status": "error",
            "message": "Please enter a farming question.",
        }), 400

    if len(message) > MAX_MESSAGE_LENGTH:
        return jsonify({
            "status": "error",
            "message": (
                f"Your message must be {MAX_MESSAGE_LENGTH} "
                "characters or fewer."
            ),
        }), 400

    # Phase 9: Fetch farmer context only for context-seeking queries
    from utils.context_chat import is_context_relevant_query
    context = None
    if is_context_relevant_query(message):
        context = _fetch_farmer_context(user_id)

    result = generate_response(message, language=language, context=context)
    reply_text = result.get("reply", "")

    # Keep the legacy API knowledge field for response compatibility.
    # The frontend must display the disease panel only for category="disease".
    if not isinstance(result.get("knowledge"), dict):
        from utils.disease_knowledge import get_disease_info
        result["knowledge"] = get_disease_info(
            "Plant condition", language=language
        )

    # Persist the conversation to MySQL chat_history table
    history_saved = False
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO chat_history (user_id, message, response)
            VALUES (%s, %s, %s)
            """,
            (user_id, message, reply_text)
        )
        connection.commit()
        history_saved = True
    except Exception as db_err:
        print(f"Could not persist chat message: {db_err}")
        if connection:
            try:
                connection.rollback()
            except Exception:
                pass
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

    response_data = {
        "status": "success",
        "reply": reply_text,
        "language": language,
        "category": result["category"],
        "history_saved": history_saved
    }

    if result.get("follow_up"):
        response_data["follow_up"] = result["follow_up"]

    if isinstance(result.get("knowledge"), dict):
        response_data["knowledge"] = result["knowledge"]

    return jsonify(response_data), 200


@chat_bp.route("/history", methods=["GET"])
def get_chat_history():
    """Retrieve historical conversations for the authenticated farmer in chronological order.

    Endpoint: GET /api/chat/history
    Optional query parameter: limit (1-100; default 50)
    """
    authorization = request.headers.get("Authorization", "")
    scheme, separator, token = authorization.partition(" ")

    if not separator or scheme.lower() != "bearer" or not token.strip():
        return jsonify({
            "status": "error",
            "message": "Authentication required. Please log in again.",
        }), 401

    user_id = get_user_id_from_token(token.strip())
    if user_id is None:
        return jsonify({
            "status": "error",
            "message": "Your session is invalid or expired. Please log in again.",
        }), 401

    limit = 50
    try:
        limit = max(1, min(int(request.args.get("limit", 50)), 100))
    except (TypeError, ValueError):
        return jsonify({
            "status": "error",
            "message": "The limit parameter must be a valid number.",
        }), 400

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, message, response, created_at
            FROM chat_history
            WHERE user_id = %s
            ORDER BY created_at DESC, id DESC
            LIMIT %s
            """,
            (user_id, limit)
        )

        rows = cursor.fetchall()
        # Reverse descending rows to present in chronological order for conversation flow
        history = []
        for row in reversed(rows):
            created_at = row.get("created_at")
            raw_msg = row.get("message") or ""
            img_match = re.search(r"\[image:(/api/chat/image/[^\]]+)\]", raw_msg)
            image_url = img_match.group(1) if img_match else None
            clean_message = re.sub(r"\[image:/api/chat/image/[^\]]+\]\s*", "", raw_msg) if image_url else raw_msg

            item = {
                "id": row["id"],
                "message": raw_msg,
                "response": row["response"],
                "created_at": created_at.isoformat() if created_at else None
            }
            if image_url:
                item["image_url"] = image_url
                item["clean_message"] = clean_message

            history.append(item)

        return jsonify({
            "status": "success",
            "count": len(history),
            "history": history
        }), 200

    except Exception as error:
        print(f"Could not retrieve chat history: {error}")
        return jsonify({
            "status": "error",
            "message": "Unable to retrieve chat history right now."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@chat_bp.route("/history", methods=["DELETE"])
def clear_chat_history():
    """Clear past conversation history for the authenticated farmer.

    Endpoint: DELETE /api/chat/history
    """
    authorization = request.headers.get("Authorization", "")
    scheme, separator, token = authorization.partition(" ")

    if not separator or scheme.lower() != "bearer" or not token.strip():
        return jsonify({
            "status": "error",
            "message": "Authentication required. Please log in again.",
        }), 401

    user_id = get_user_id_from_token(token.strip())
    if user_id is None:
        return jsonify({
            "status": "error",
            "message": "Your session is invalid or expired. Please log in again.",
        }), 401

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM chat_history
            WHERE user_id = %s
            """,
            (user_id,)
        )
        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Chat history cleared successfully."
        }), 200

    except Exception as error:
        print(f"Could not clear chat history: {error}")
        return jsonify({
            "status": "error",
            "message": "Unable to clear chat history right now."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@chat_bp.route("/image/<filename>", methods=["GET"])
def get_chat_image(filename):
    """Serve uploaded chat leaf image with strict path traversal checks and farmer isolation."""
    safe_name = secure_filename(filename)
    if not safe_name or safe_name != filename:
        return jsonify({"status": "error", "message": "Invalid image filename."}), 400

    file_path = os.path.join(UPLOADS_DIR, safe_name)
    if not os.path.isfile(file_path):
        return jsonify({"status": "error", "message": "Image not found."}), 404

    # Security check: verify authentication
    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):].strip()
    elif request.args.get("token"):
        token = request.args.get("token").strip()

    if not token:
        return jsonify({"status": "error", "message": "Authentication required to access this image."}), 401

    user_id = get_user_id_from_token(token)
    if user_id is None:
        return jsonify({"status": "error", "message": "Invalid or expired session token."}), 401

    # Strict isolation: check filename pattern chat_leaf_{user_id}_
    expected_prefix = f"chat_leaf_{user_id}_"
    if not safe_name.startswith(expected_prefix):
        # Fallback check if user owns any message referencing this image
        is_owner = False
        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT id FROM chat_history WHERE user_id = %s AND message LIKE %s LIMIT 1",
                (user_id, f"%{safe_name}%")
            )
            if cursor.fetchone():
                is_owner = True
        except Exception:
            pass
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

        if not is_owner:
            return jsonify({"status": "error", "message": "Access denied to this image."}), 403

    return send_from_directory(UPLOADS_DIR, safe_name)
