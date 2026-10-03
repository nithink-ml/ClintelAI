"""PHI-Safe, structured logging system for ClintelAI."""

import logging
import re
import sys

# Patterns for sensitive keywords, credentials, PII, and precise coordinates that should never be logged
SENSITIVE_PATTERNS = [
    # JWT Bearer tokens
    (re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]+", re.IGNORECASE), "Bearer [REDACTED_TOKEN]"),
    # Raw JWT tokens
    (
        re.compile(r"\bey[a-zA-Z0-9_\-]{20,}\.[a-zA-Z0-9_\-]{20,}\.[a-zA-Z0-9_\-]+\b"),
        "[REDACTED_JWT]",
    ),
    # Passwords, API keys, and secret credentials
    (
        re.compile(
            r"((?:password|client_secret|secret|api[-_]?key|refresh_token|access_token)\s*[:=]\s*['\"]?)[^'\"&\s,]+(['\"]?)",
            re.IGNORECASE,
        ),
        r"\g<1>[REDACTED_SECRET]\g<2>",
    ),
    # Email addresses (PII)
    (
        re.compile(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b"),
        "[REDACTED_EMAIL]",
    ),
    # Phone numbers (Indian 10-digit mobile)
    (
        re.compile(r"(?:\+91[\-\s]?)?[6-9]\d{9}\b"),
        "[REDACTED_PHONE]",
    ),
    # Aadhaar-like 12-digit identity numbers
    (
        re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b"),
        "[REDACTED_AADHAAR]",
    ),
    # High-precision coordinates (coarsen to prevent patient tracking leakage)
    (
        re.compile(r"((?:latitude|longitude|lat|lon|lng)\s*[:=]\s*)(-?\d+\.\d{3,})", re.IGNORECASE),
        r"\g<1>[COARSE_GEO]",
    ),
]


class SensitiveDataFilter(logging.Filter):
    """Redacts potential tokens, passwords, patient health markers, and precise coordinates from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, replacement in SENSITIVE_PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        return True


def setup_logging(debug: bool = False) -> logging.Logger:
    """Configures structured console logging with redaction filters."""
    logger = logging.getLogger("clintelai")
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Avoid duplicate handlers if re-called
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [clintelai] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )
        handler.setFormatter(formatter)
        handler.addFilter(SensitiveDataFilter())
        logger.addHandler(handler)

    return logger


logger = setup_logging()
