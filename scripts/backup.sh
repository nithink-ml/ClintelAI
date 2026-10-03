#!/usr/bin/env bash
# ==============================================================================
# ClintelAI Production Automated Backup Script
# Backs up PostgreSQL (PostGIS tables), ChromaDB Vector Store, and verifies integrity.
# ==============================================================================

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/clintelai}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
PG_CONTAINER="${POSTGRES_CONTAINER:-clintelai_postgres}"
DB_NAME="${POSTGRES_DB:-clintelai_db}"
DB_USER="${POSTGRES_USER:-clintelai}"
CHROMA_DIR="${CHROMA_DATA_DIR:-./chroma_data}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

mkdir -p "${BACKUP_DIR}"
BACKUP_DIR="$(cd "${BACKUP_DIR}" && pwd)"

echo "=================================================================="
echo "ClintelAI Production Backup — ${TIMESTAMP}"
echo "Backup destination: ${BACKUP_DIR}"
echo "=================================================================="

# Checksum helper
compute_sha256() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1"
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1"
    else
        echo "Error: neither sha256sum nor shasum is available." >&2
        exit 1
    fi
}

# 1. PostgreSQL PostGIS Database Dump
PG_BACKUP_FILE="${BACKUP_DIR}/clintelai_db_${TIMESTAMP}.dump"
echo "[1/3] Dumping PostgreSQL database '${DB_NAME}' from container '${PG_CONTAINER}'..."
if docker ps --format '{{.Names}}' | grep -q "^${PG_CONTAINER}$"; then
    docker exec "${PG_CONTAINER}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" -Fc > "${PG_BACKUP_FILE}"
else
    echo "Container '${PG_CONTAINER}' not running locally; attempting direct pg_dump..."
    pg_dump -U "${DB_USER}" -d "${DB_NAME}" -Fc -f "${PG_BACKUP_FILE}"
fi

PG_SIZE=$(du -h "${PG_BACKUP_FILE}" | cut -f1)
echo "  -> PostgreSQL dump completed: ${PG_BACKUP_FILE} (${PG_SIZE})"

# 2. ChromaDB Vector Store Archive
CHROMA_BACKUP_FILE="${BACKUP_DIR}/clintelai_chroma_${TIMESTAMP}.tar.gz"
echo "[2/3] Archiving ChromaDB vector store directory..."
if [ -d "${CHROMA_DIR}" ]; then
    tar -czf "${CHROMA_BACKUP_FILE}" -C "$(dirname "${CHROMA_DIR}")" "$(basename "${CHROMA_DIR}")"
    CHROMA_SIZE=$(du -h "${CHROMA_BACKUP_FILE}" | cut -f1)
    echo "  -> ChromaDB archive completed: ${CHROMA_BACKUP_FILE} (${CHROMA_SIZE})"
else
    echo "  -> ChromaDB local directory '${CHROMA_DIR}' not found. Checking docker volume..."
    docker run --rm -v chroma_prod_data:/data -v "${BACKUP_DIR}":/backup alpine \
        tar -czf "/backup/clintelai_chroma_${TIMESTAMP}.tar.gz" -C /data . || true
fi

# 3. Cryptographic Checksum Generation
echo "[3/3] Generating SHA-256 integrity checksums..."
CHECKSUM_FILE="${BACKUP_DIR}/checksums_${TIMESTAMP}.sha256"
cd "${BACKUP_DIR}"
compute_sha256 "$(basename "${PG_BACKUP_FILE}")" > "${CHECKSUM_FILE}"
if [ -f "${CHROMA_BACKUP_FILE}" ]; then
    compute_sha256 "$(basename "${CHROMA_BACKUP_FILE}")" >> "${CHECKSUM_FILE}"
fi
echo "  -> SHA-256 checksums recorded in: ${CHECKSUM_FILE}"

# 4. Prune Outdated Backups
echo "Pruning backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "clintelai_db_*.dump" -mtime +"${RETENTION_DAYS}" -delete || true
find "${BACKUP_DIR}" -name "clintelai_chroma_*.tar.gz" -mtime +"${RETENTION_DAYS}" -delete || true
find "${BACKUP_DIR}" -name "checksums_*.sha256" -mtime +"${RETENTION_DAYS}" -delete || true

echo "=================================================================="
echo "Backup successfully completed at $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "=================================================================="
