from __future__ import annotations

import io
import json
import logging

from app import logging as mylog


def test_redact():
    assert mylog.redact({"token": "secret"})["token"] == "***"
    assert mylog.redact({"a": {"password": "x"}})["a"]["password"] == "***"
    assert mylog.redact({"safe": 1}) == {"safe": 1}
    assert mylog.redact(["ok", {"Authorization": "Bearer z"}])[1]["Authorization"] == "***"


def test_log_emits_json():
    mylog.configure_logging()
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(mylog.JsonFormatter())
    logging.getLogger().handlers = [handler]
    mylog.log(logging.INFO, "hello", token="xyz", bot_id="bot_1")
    line = buf.getvalue().strip()
    data = json.loads(line)
    assert data["msg"] == "hello"
    assert data["token"] == "***"
    assert data["bot_id"] == "bot_1"
