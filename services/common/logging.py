from __future__ import annotations

import contextvars
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")
conversation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("conversation_id", default="")


class JsonFormatter(logging.Formatter):
    """Structured JSON log formatter with request_id and conversation_id (pseudonymous IDs only)."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get() or None,
            "conversation_id": conversation_id_var.get() or None,
        }
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def get_logger(name: str = "keepwell") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def new_request_id() -> str:
    rid = str(uuid.uuid4())
    request_id_var.set(rid)
    return rid
