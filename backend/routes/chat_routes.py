"""Authenticated API endpoints for the AgriSmart farming assistant."""

from flask import Blueprint, jsonify, request
from config import get_db_connection
from utils.auth_tokens import get_user_id_from_token
from utils.chatbot import MAX_MESSAGE_LENGTH, generate_response

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")


@chat_bp.route("/message", methods=["POST"])
def chat_message():
    """Answer one farming question from an authenticated user and persist to history."""
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

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "Send a JSON object containing a message.",
        }), 400

    message = data.get("message")
    if not isinstance(message, str) or not message.strip():
        return jsonify({
            "status": "error",
            "message": "Please enter a farming question.",
        }), 400

    message = message.strip()
    if len(message) > MAX_MESSAGE_LENGTH:
        return jsonify({
            "status": "error",
            "message": (
                f"Your message must be {MAX_MESSAGE_LENGTH} "
                "characters or fewer."
            ),
        }), 400

    # Valid explicit languages are respected. Missing/"auto" detects the message;
    # invalid explicit language codes safely fall back to English.
    requested_language = data.get("language")
    if requested_language in ("en", "mr", "hi"):
        language = requested_language
    elif requested_language is None or requested_language == "auto":
        from utils.chatbot import _detect_language
        language = _detect_language(message)
        if language not in ("en", "mr", "hi"):
            language = "en"
    else:
        language = "en"

    result = generate_response(message, language=language)
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
            history.append({
                "id": row["id"],
                "message": row["message"],
                "response": row["response"],
                "created_at": created_at.isoformat() if created_at else None
            })

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
