#!/usr/bin/env bash
# =============================================================================
# AgriSmart Database Restoration Script
# Safely restores a compressed or raw MySQL dump file into the database.
# =============================================================================

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <path-to-backup-file.sql[.gz]>"
    exit 1
fi

BACKUP_FILE="$1"
if [[ ! -f "${BACKUP_FILE}" ]]; then
    echo "Error: Backup file '${BACKUP_FILE}' not found."
    exit 1
fi

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

read -p "WARNING: This will overwrite data in '${DB_NAME}' on ${DB_HOST}. Are you sure? [y/N]: " CONFIRM
if [[ "${CONFIRM}" != "y" && "${CONFIRM}" != "Y" ]]; then
    echo "Restoration aborted."
    exit 0
fi

echo "[AgriSmart Restore] Restoring from ${BACKUP_FILE} into ${DB_NAME}..."

if [[ "${BACKUP_FILE}" == *.gz ]]; then
    gunzip -c "${BACKUP_FILE}" | mysql --host="${DB_HOST}" --port="${DB_PORT}" --user="${DB_USER}" --password="${DB_PASSWORD}" "${DB_NAME}"
else
    mysql --host="${DB_HOST}" --port="${DB_PORT}" --user="${DB_USER}" --password="${DB_PASSWORD}" "${DB_NAME}" < "${BACKUP_FILE}"
fi

echo "[AgriSmart Restore] Database restoration successfully completed."
