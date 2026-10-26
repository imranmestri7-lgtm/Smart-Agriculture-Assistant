"""Authenticated API endpoints for the AgriSmart farming assistant."""

from flask import Blueprint, jsonify, request

from utils.auth_tokens import get_user_id_from_token
from utils.chatbot import MAX_MESSAGE_LENGTH, generate_response

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")


@chat_bp.route("/message", methods=["POST"])
def chat_message():
    """Answer one farming question from an authenticated user."""
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
    # Keep the legacy API knowledge field for response compatibility.
    # The frontend must display the disease panel only for category="disease".
    if not isinstance(result.get("knowledge"), dict):
        from utils.disease_knowledge import get_disease_info
        result["knowledge"] = get_disease_info(
            "Plant condition", language=language
        )

    response_data = {
        "status": "success",
        "reply": result["reply"],
        "category": result["category"],
    }

    if result.get("follow_up"):
        response_data["follow_up"] = result["follow_up"]

    if isinstance(result.get("knowledge"), dict):
        response_data["knowledge"] = result["knowledge"]

    return jsonify(response_data), 200