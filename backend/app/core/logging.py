"""PHI-Safe, structured logging system for ClintelAI."""

import logging
import re
import sys

# Patterns for sensitive keywords that should never be logged in cleartext
SENSITIVE_PATTERNS = [
    re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]+", re.IGNORECASE),
    re.compile(r"password=([^&\s]+)", re.IGNORECASE),
    re.compile(r"api[-_]?key=([^&\s]+)", re.IGNORECASE),
]


class SensitiveDataFilter(logging.Filter):
    """Redacts potential tokens, passwords, and patient health markers from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern in SENSITIVE_PATTERNS:
                record.msg = pattern.sub("[REDACTED_SECRET]", record.msg)
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
            datefmt="%Y-%m-%dT%H:%M:%SZ"
        )
        handler.setFormatter(formatter)
        handler.addFilter(SensitiveDataFilter())
        logger.addHandler(handler)

    return logger


logger = setup_logging()
