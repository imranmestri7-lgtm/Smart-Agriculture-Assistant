"""AgriSmart Backend Server.

Configured with production-ready security controls:
- Hardened static file serving (blocks .env, hidden files, backend source traversal)
- Security headers (X-Content-Type-Options, X-Frame-Options, XSS, Referrer-Policy, HSTS)
- Request size limit enforcement (MAX_CONTENT_LENGTH)
- Configurable production CORS origins
- Safe error handlers preventing stack trace exposure
- Clean extensionless frontend route handling
"""

import os
import secrets
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

try:
    import mysql.connector
except ImportError:
    class _DummyMySQL:
        class Error(Exception):
            pass
    mysql = _DummyMySQL()

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
from routes.financial_routes import financial_bp
from routes.activity_routes import activity_bp

app = Flask(__name__)

# Security & Request Limits
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", os.getenv("JWT_SECRET_KEY", secrets.token_hex(32)))

# CORS Configuration
cors_origins_env = os.getenv("CORS_ALLOWED_ORIGINS")
if cors_origins_env and cors_origins_env.strip() != "*":
    allowed_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
    CORS(app, origins=allowed_origins, supports_credentials=True)
else:
    CORS(app)

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(disease_bp)
app.register_blueprint(irrigation_bp)
app.register_blueprint(weather_bp)
app.register_blueprint(crop_bp)
app.register_blueprint(farm_bp)
app.register_blueprint(crop_mgmt_bp)
app.register_blueprint(analytics_bp)
app.register_blueprint(notification_bp)
app.register_blueprint(iot_bp)
app.register_blueprint(financial_bp)
app.register_blueprint(activity_bp)


# =========================================================================
# SECURITY HEADERS (Defense-in-depth)
# =========================================================================

@app.after_request
def apply_security_headers(response):
    """Attach defensive security headers to all responses."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Enforce HSTS for secure connections (HTTPS / proxy)
    if request.is_secure or request.headers.get("X-Forwarded-Proto") == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    # Prevent shared proxies or browser HTTP caching of private user API data
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response.headers["Pragma"] = "no-cache"

    return response


# =========================================================================
# CENTRALIZED ERROR HANDLERS
# =========================================================================

@app.errorhandler(413)
def payload_too_large(error):
    return jsonify({
        "status": "error",
        "message": "Request payload exceeds maximum allowed size (16 MB)."
    }), 413


@app.errorhandler(404)
def not_found_handler(error):
    return jsonify({
        "status": "error",
        "message": "The requested resource was not found."
    }), 404


@app.errorhandler(500)
def server_error_handler(error):
    # Log internal error but do not leak details to clients
    return jsonify({
        "status": "error",
        "message": "An internal server error occurred. Please try again later."
    }), 500


# =========================================================================
# SYSTEM DIAGNOSTIC ROUTES
# =========================================================================

@app.route("/")
def home():
    # If a browser or webview requests the root URL expecting HTML, serve index.html
    # while preserving the standard JSON health check response for API callers / automated tests
    accept = request.headers.get("Accept", "")
    if "text/html" in accept and not request.path.startswith("/api"):
        return send_from_directory(PROJECT_ROOT, "index.html")
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
        # Sanitized database error
        return jsonify({
            "status": "error",
            "message": "Database connection check failed."
        }), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# =========================================================================
# PROGRESSIVE WEB APP & STATIC FRONTEND SERVING
# =========================================================================

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ALLOWED_FRONTEND_EXTENSIONS = {
    ".html", ".css", ".js", ".json", ".webmanifest",
    ".png", ".jpg", ".jpeg", ".svg", ".ico", ".webp",
    ".woff", ".woff2", ".ttf", ".eot", ".map", ".txt"
}

FORBIDDEN_PATH_PREFIXES = (
    "backend", "tests", "migrations", "ml", "brain", "scratch",
    "venv", "venv-python39", ".git", ".env"
)

CLEAN_URL_MAP = {
    "login": "login.html",
    "register": "register.html",
    "farmer": "farmer.html",
    "disease": "disease.html",
    "crop": "crop.html",
    "weather": "weather.html",
    "irrigation": "irrigation.html",
    "offline": "offline.html",
    "index": "index.html",
}


@app.route("/sw.js")
def service_worker():
    response = send_from_directory(PROJECT_ROOT, "sw.js")
    response.headers["Content-Type"] = "application/javascript"
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@app.route("/manifest.json")
def manifest():
    response = send_from_directory(PROJECT_ROOT, "manifest.json")
    response.headers["Content-Type"] = "application/manifest+json"
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response


@app.route("/offline.html")
def offline_page():
    return send_from_directory(PROJECT_ROOT, "offline.html")


@app.route("/<path:filename>")
def serve_frontend(filename):
    """Safely serve frontend static assets while strictly blocking internal files."""
    normalized_rel = os.path.normpath(filename).replace("\\", "/")

    # Unmatched API paths should return 404 Not Found, not attempt frontend serving
    if normalized_rel == "api" or normalized_rel.startswith("api/"):
        return jsonify({"status": "error", "message": "API endpoint not found."}), 404

    # 1. Clean extensionless URLs (e.g., /login -> login.html)
    clean_slug = filename.strip("/").lower()
    if clean_slug in CLEAN_URL_MAP:
        filename = CLEAN_URL_MAP[clean_slug]

    # 2. Block hidden files and paths starting with dot (e.g. .env, .git, .DS_Store)
    parts = filename.replace("\\", "/").split("/")
    if any(p.startswith(".") for p in parts if p):
        return jsonify({"status": "error", "message": "Access denied."}), 403

    # 3. Block sensitive backend or internal paths
    normalized_rel = os.path.normpath(filename).replace("\\", "/")
    for forbidden in FORBIDDEN_PATH_PREFIXES:
        if normalized_rel == forbidden or normalized_rel.startswith(forbidden + "/"):
            return jsonify({"status": "error", "message": "Access denied."}), 403

    # 4. Resolve full path and enforce boundary
    safe_path = os.path.normpath(os.path.join(PROJECT_ROOT, filename))
    try:
        common = os.path.commonpath([PROJECT_ROOT, safe_path])
    except ValueError:
        return jsonify({"status": "error", "message": "Access denied."}), 403

    if common != PROJECT_ROOT or not os.path.isfile(safe_path):
        return jsonify({"status": "error", "message": "File not found"}), 404

    # 5. Check allowed frontend extensions
    _, ext = os.path.splitext(safe_path)
    if ext.lower() not in ALLOWED_FRONTEND_EXTENSIONS:
        return jsonify({"status": "error", "message": "Access denied."}), 403

    return send_from_directory(PROJECT_ROOT, filename)


if __name__ == "__main__":
    debug_env = os.getenv("FLASK_DEBUG", "false").lower() in ("true", "1", "t")
    server_port = int(os.getenv("PORT", os.getenv("FLASK_PORT", 5000)))
    app.run(host="0.0.0.0", port=server_port, debug=debug_env)
