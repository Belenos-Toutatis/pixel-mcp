"""Structured JSON-lines logging for pixel-mcp.

Logs vers ~/.config/pixel-mcp/logs/pixel-mcp.log (rotation 5x1Mo).
Niveau via env var PIXEL_MCP_LOG_LEVEL (DEBUG|INFO|WARNING|ERROR), défaut INFO.

Aucun secret (Authorization header, tokens, client_secret) ni payload de data
points individuel (FC, sommeil, GPS…) n'est loggé. On loggue uniquement
méta-info HTTP (méthode, path, status, durée).
"""

from __future__ import annotations

import json
import logging
import os
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

LOG_DIR = Path(os.path.expanduser("~/.config/pixel-mcp/logs"))
LOG_FILE = LOG_DIR / "pixel-mcp.log"
LOGGER_NAME = "pixel-mcp"

_configured = False


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        for k, v in record.__dict__.items():
            if k in (
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
                "taskName",
            ):
                continue
            payload[k] = v
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging() -> logging.Logger:
    global _configured
    logger = logging.getLogger(LOGGER_NAME)
    if _configured:
        return logger

    level_name = os.environ.get("PIXEL_MCP_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(level)
    logger.propagate = False

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    handler.setFormatter(_JsonFormatter())
    logger.addHandler(handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    _configured = True
    logger.info("logging initialized", extra={"event": "startup", "level": level_name})
    return logger


def get_logger() -> logging.Logger:
    return setup_logging()
