#!/usr/bin/env bash
# =============================================================================
# AgriSmart Production Deployment Script
# Automates zero-downtime deployment, migrations, and health verification.
# =============================================================================

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="${ROOT_DIR}/backend"
VENV_DIR="${BACKEND_DIR}/venv"

echo "================================================================="
echo "Starting AgriSmart Production Deployment"
echo "================================================================="

cd "${ROOT_DIR}"

# 1. Check environment file
if [[ ! -f "${BACKEND_DIR}/.env" ]]; then
    echo "ERROR: ${BACKEND_DIR}/.env is missing. Create it from .env.production.example."
    exit 1
fi

# 2. Verify model file exists
MODEL_FILE="${BACKEND_DIR}/models/plant_disease_model.keras"
if [[ ! -f "${MODEL_FILE}" ]]; then
    echo "ERROR: TensorFlow model file ${MODEL_FILE} not found."
    exit 1
fi
echo "[Check] TensorFlow plant disease model is present ($(du -h "${MODEL_FILE}" | cut -f1))."

# 3. Update dependencies
echo "[Step 1] Updating Python dependencies..."
"${VENV_DIR}/bin/pip" install --upgrade pip --quiet
"${VENV_DIR}/bin/pip" install -r "${ROOT_DIR}/requirements-prod.txt" --quiet

# 4. Run idempotent database migrations
echo "[Step 2] Executing database schema migrations..."
PYTHONPATH="${ROOT_DIR}:${BACKEND_DIR}" "${VENV_DIR}/bin/python3" "${BACKEND_DIR}/migrations/run_migrations.py"

# 5. Execute regression test suite
echo "[Step 3] Running automated regression suite..."
PYTHONPATH="${ROOT_DIR}:${BACKEND_DIR}" "${VENV_DIR}/bin/python3" -m unittest discover -s "${BACKEND_DIR}/tests"

# 6. Ensure permissions on uploads and keras_config
echo "[Step 4] Ensuring writable storage directories..."
mkdir -p "${BACKEND_DIR}/uploads" "${BACKEND_DIR}/keras_config"
chmod -R 755 "${BACKEND_DIR}/uploads" "${BACKEND_DIR}/keras_config"

# 7. Reload WSGI server
echo "[Step 5] Gracefully reloading WSGI server..."
if systemctl is-active --quiet agrismart; then
    sudo systemctl reload agrismart
    echo "[Deploy] Systemd service 'agrismart' reloaded."
elif command -v docker &> /dev/null && docker compose ps web &> /dev/null; then
    docker compose restart web
    echo "[Deploy] Docker compose web service restarted."
else
    echo "[Notice] Running standalone or manual WSGI. Restart Gunicorn if active."
fi

# 8. Post-deployment healthcheck
echo "[Step 6] Running endpoint healthcheck..."
sleep 2
HEALTH_URL="http://127.0.0.1:5000/api/test"
if command -v curl &> /dev/null; then
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${HEALTH_URL}" || echo "000")
    if [[ "${HTTP_STATUS}" == "200" ]]; then
        echo "[Healthcheck OK] Backend is responding with HTTP 200."
    else
        echo "[Healthcheck WARNING] Backend returned HTTP ${HTTP_STATUS}."
    fi
fi

echo "================================================================="
echo "AgriSmart Production Deployment Completed Successfully!"
echo "================================================================="
