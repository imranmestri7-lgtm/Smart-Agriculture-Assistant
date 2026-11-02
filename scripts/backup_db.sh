#!/usr/bin/env bash
# =============================================================================
# AgriSmart Automated Database Backup Script
# Creates compressed, timestamped MySQL database backups with retention policy.
# =============================================================================

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/agrismart}"
RETENTION_DAYS=14
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/agrismart_db_${TIMESTAMP}.sql.gz"

# Source environment if present
ENV_FILE="$(dirname "$0")/../backend/.env"
if [[ -f "${ENV_FILE}" ]]; then
    # shellcheck disable=SC1090
    export $(grep -v '^#' "${ENV_FILE}" | xargs)
fi

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
DB_USER="${DB_USER:-root}"
DB_PASSWORD="${DB_PASSWORD:-}"
DB_NAME="${DB_NAME:-smart_agriculture}"

mkdir -p "${BACKUP_DIR}"

echo "[AgriSmart Backup] Starting MySQL dump for database '${DB_NAME}' at ${TIMESTAMP}..."

# Execute mysqldump with single transaction (safe for production InnoDB without table locks)
mysqldump \
    --host="${DB_HOST}" \
    --port="${DB_PORT}" \
    --user="${DB_USER}" \
    --password="${DB_PASSWORD}" \
    --single-transaction \
    --quick \
    --routines \
    --triggers \
    "${DB_NAME}" | gzip -9 > "${BACKUP_FILE}"

FILESIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
echo "[AgriSmart Backup] Successfully created ${BACKUP_FILE} (${FILESIZE})"

# Remove backups older than RETENTION_DAYS
echo "[AgriSmart Backup] Pruning backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "agrismart_db_*.sql.gz" -type f -mtime +"${RETENTION_DAYS}" -delete

echo "[AgriSmart Backup] Backup procedure complete."
