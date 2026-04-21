"""Telegram webhook Lambda.

Invoked by a Lambda Function URL. Path is `/<webhookPath>`.
Flow:
  1. Parse body.
  2. Query DynamoDB GSI1 by webhookPath → Bot item.
  3. Verify X-Telegram-Bot-Api-Secret-Token header.
  4. Match `/command` against bot.commands → send reply via sendMessage.
  5. Write trimmed event to DynamoDB.
  6. Always return 200 (Telegram retries aggressively on 5xx).
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
import uuid
from datetime import UTC, datetime
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

REGION = os.environ.get("AWS_REGION", "ap-southeast-2")
TABLE_NAME = os.environ.get("TABLE_NAME", "mcp_platform_prod")
SECRETS_PREFIX = os.environ.get("SECRETS_PREFIX", "mcp-platform")

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _table():
    return boto3.resource("dynamodb", region_name=REGION).Table(TABLE_NAME)


def _sm():
    return boto3.client("secretsmanager", region_name=REGION)


def _log(msg: str, **fields: Any) -> None:
    fields["msg"] = msg
    logger.info(json.dumps(fields, default=str))


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _get_bot_by_path(path: str) -> dict[str, Any] | None:
    res = _table().query(
        IndexName="GSI1",
        KeyConditionExpression=Key("GSI1PK").eq(f"WEBHOOK#{path}") & Key("GSI1SK").eq("BOT"),
        Limit=1,
    )
    items = res.get("Items", [])
    return items[0] if items else None


def _get_secret(tenant_id: str, secret_id: str) -> str:
    name = f"{SECRETS_PREFIX}/{tenant_id}/{secret_id}"
    return _sm().get_secret_value(SecretId=name)["SecretString"]


def _send_message(token: str, chat_id: int | str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = json.dumps({"chat_id": chat_id, "text": text}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as resp:  # noqa: S310
        resp.read()


def _put_event(bot_id: str, event_type: str, msg: str, details: dict[str, Any]) -> None:
    ts = _now_iso()
    ev_id = f"ev_{uuid.uuid4().hex[:10]}"
    _table().put_item(
        Item={
            "PK": f"BOT#{bot_id}",
            "SK": f"EVENT#{ts}#{ev_id}",
            "GSI2PK": f"BOT#{bot_id}",
            "GSI2SK": f"EVENT#{ts}",
            "id": ev_id,
            "botId": bot_id,
            "ts": ts,
            "type": event_type,
            "msg": msg,
            "actor": "telegram-api",
            "details": details,
            "ttl": int(time.time() + 30 * 86400),
        }
    )


def _match_command(commands: list[dict[str, Any]], text: str) -> str | None:
    if not text:
        return None
    first = text.split()[0]
    for c in commands:
        cmd = c.get("cmd", "")
        # Telegram sends /cmd@BotName in groups; match the prefix before @.
        if first == cmd or first.split("@", 1)[0] == cmd:
            return c.get("template")
    return None


def _ok() -> dict[str, Any]:
    return {"statusCode": 200, "body": ""}


def handler(event: dict[str, Any], _context: object) -> dict[str, Any]:
    start = time.time()
    trace_id = uuid.uuid4().hex[:10]
    try:
        path = event.get("rawPath", "").strip("/")
        if not path:
            _log("webhook.no_path", trace_id=trace_id)
            return _ok()

        headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
        body_raw = event.get("body") or "{}"
        try:
            body = json.loads(body_raw)
        except json.JSONDecodeError:
            _log("webhook.bad_json", trace_id=trace_id)
            return _ok()

        bot = _get_bot_by_path(path)
        if not bot:
            _log("webhook.unknown_path", trace_id=trace_id, path=path)
            return _ok()

        bot_id: str = bot["id"]
        tenant_id: str = bot["tenantId"]

        if bot.get("status") != "deployed":
            _log("webhook.not_deployed", trace_id=trace_id, bot_id=bot_id, status=bot.get("status"))
            return _ok()

        # Verify shared secret token.
        try:
            expected = _get_secret(tenant_id, f"{bot_id}/webhook-secret")
        except Exception as e:
            _log("webhook.secret_fetch_failed", trace_id=trace_id, bot_id=bot_id, error=str(e))
            return _ok()

        given = headers.get("x-telegram-bot-api-secret-token", "")
        if given != expected:
            _put_event(
                bot_id,
                "webhook.bad_token",
                "rejected (bad secret token)",
                {"trace_id": trace_id},
            )
            _log("webhook.bad_token", trace_id=trace_id, bot_id=bot_id)
            return _ok()

        message = body.get("message") or {}
        text: str = (message.get("text") or "").strip()
        chat = message.get("chat") or {}
        chat_id = chat.get("id")

        reply = _match_command(bot.get("commands") or [], text)
        sent = False
        if reply and chat_id is not None:
            try:
                token = _get_secret(tenant_id, bot["secretId"])
                _send_message(token, chat_id, reply)
                sent = True
            except Exception as e:
                _log("webhook.send_failed", trace_id=trace_id, bot_id=bot_id, error=str(e))
                _put_event(bot_id, "webhook.error", f"sendMessage failed: {e}", {"trace_id": trace_id})

        _put_event(
            bot_id,
            "webhook.received",
            f"{text[:80]}" if text else "(no text)",
            {
                "trace_id": trace_id,
                "chat_id": chat_id,
                "matched": bool(reply),
                "sent": sent,
                "text": text[:500],
            },
        )
        _log(
            "webhook.ok",
            trace_id=trace_id,
            bot_id=bot_id,
            matched=bool(reply),
            sent=sent,
            latency_ms=int((time.time() - start) * 1000),
        )
        return _ok()
    except Exception as e:
        _log("webhook.unhandled", trace_id=trace_id, error=str(e))
        return _ok()  # never 5xx
