"""Structured JSON logging with automatic redaction of sensitive fields."""

from __future__ import annotations

import json
import logging
import re
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any

_REDACT_KEY = re.compile(r"(token|value|password|secret_value|authorization)", re.I)
_trace_id: ContextVar[str] = ContextVar("trace_id", default="-")


def new_trace_id() -> str:
    tid = uuid.uuid4().hex[:12]
    _trace_id.set(tid)
    return tid


def redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: ("***" if _REDACT_KEY.search(k) else redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(x) for x in obj]
    return obj


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "msg": record.getMessage(),
            "trace_id": _trace_id.get(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        extras = getattr(record, "extra_fields", None)
        if extras:
            payload.update(redact(extras))
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def log(level: int, msg: str, **fields: Any) -> None:
    logger = logging.getLogger("mcp")
    record = logger.makeRecord("mcp", level, "-", 0, msg, (), None, extra={"extra_fields": fields})
    logger.handle(record)
