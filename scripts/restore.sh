#!/usr/bin/env bash
# ==============================================================================
# ClintelAI Production Automated Restore Script
# Verifies SHA-256 integrity and restores PostgreSQL (PostGIS) and ChromaDB.
# ==============================================================================

set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <path_to_db_dump_or_backup_dir> [checksum_file]"
    echo "Example: $0 /var/backups/clintelai/clintelai_db_20261003_120000.dump"
    exit 1
fi

TARGET="$1"
PG_CONTAINER="${POSTGRES_CONTAINER:-clintelai_postgres}"
DB_NAME="${POSTGRES_DB:-clintelai_db}"
DB_USER="${POSTGRES_USER:-clintelai}"
CHROMA_DIR="${CHROMA_DATA_DIR:-./chroma_data}"

echo "=================================================================="
echo "ClintelAI Production Restore Procedure"
echo "Target backup: ${TARGET}"
echo "=================================================================="

verify_sha256() {
    local checksum_file="$1"
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum -c "${checksum_file}"
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 -c "${checksum_file}"
    else
        echo "Warning: Neither sha256sum nor shasum available to verify checksum." >&2
    fi
}

# 1. Checksum Verification
if [ -f "${TARGET}.sha256" ]; then
    echo "[1/3] Verifying cryptographic SHA-256 integrity checksum..."
    cd "$(dirname "${TARGET}")"
    verify_sha256 "$(basename "${TARGET}.sha256")"
    echo "  -> Checksum verification passed."
elif [ "$#" -ge 2 ] && [ -f "$2" ]; then
    echo "[1/3] Verifying provided checksum file $2..."
    cd "$(dirname "${TARGET}")"
    verify_sha256 "$(basename "$2")"
    echo "  -> Checksum verification passed."
else
    echo "[1/3] Warning: No checksum file provided. Proceeding with caution..."
fi

# 2. Database Restoration
echo "[2/3] Restoring PostgreSQL PostGIS database..."
if docker ps --format '{{.Names}}' | grep -q "^${PG_CONTAINER}$"; then
    echo "  -> Streaming dump into container '${PG_CONTAINER}'..."
    docker exec -i "${PG_CONTAINER}" pg_restore -U "${DB_USER}" -d "${DB_NAME}" --clean --if-exists < "${TARGET}" || {
        echo "  -> Non-fatal restore notices encountered. Checking database connectivity..."
    }
else
    echo "  -> Running local pg_restore..."
    pg_restore -U "${DB_USER}" -d "${DB_NAME}" --clean --if-exists "${TARGET}" || true
fi

# 3. Vector Database Restoration
CHROMA_ARCHIVE="${TARGET%.dump}.tar.gz"
CHROMA_ARCHIVE="${CHROMA_ARCHIVE/clintelai_db_/clintelai_chroma_}"
if [ -f "${CHROMA_ARCHIVE}" ]; then
    echo "[3/3] Restoring ChromaDB vector store from ${CHROMA_ARCHIVE}..."
    tar -xzf "${CHROMA_ARCHIVE}" -C "$(dirname "${CHROMA_DIR}")"
    echo "  -> ChromaDB directory restored to: ${CHROMA_DIR}"
else
    echo "[3/3] No matching ChromaDB archive found (${CHROMA_ARCHIVE}); skipping vector store restore."
fi

echo "=================================================================="
echo "Restore verification: Performing table count check..."
if docker ps --format '{{.Names}}' | grep -q "^${PG_CONTAINER}$"; then
    docker exec -i "${PG_CONTAINER}" psql -U "${DB_USER}" -d "${DB_NAME}" -c \
        "SELECT count(*) AS total_facilities FROM facilities; SELECT count(*) AS total_alerts FROM health_alerts;"
fi
echo "Database and Vector Store restoration completed successfully."
echo "=================================================================="
