"""Telegram webhook Lambda.

Invoked by a Lambda Function URL. Path is `/<webhookPath>`.
Flow:
  1. Parse body.
  2. Query DynamoDB GSI1 by webhookPath → Bot item.
  3. Verify X-Telegram-Bot-Api-Secret-Token header.
  4. Resolve a function for the message:
       - slash command → matching `commands[*].function`, falling back to
         `defaultFunction` if the command has no override.
       - non-slash text → `defaultFunction`.
       - unknown slash → `defaultFunction`.
  5. Invoke the function (currently: AWS Bedrock AgentCore harness) and
     reply via sendMessage.
  6. Write trimmed event to DynamoDB.
  7. Always return 200 (Telegram retries aggressively on 5xx).
"""

from __future__ import annotations

import hashlib
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


def _bedrock():
    return boto3.client("bedrock-agentcore", region_name=REGION)


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
    with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
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


def _resolve_function(bot: dict[str, Any], text: str) -> tuple[dict | None, bool, str | None]:
    """Pick the function to invoke for a given message.

    Returns (function_dict, matched_slash_command, matched_cmd_name).
    """
    default_fn = bot.get("defaultFunction")
    if text.startswith("/"):
        first = text.split()[0].split("@", 1)[0]
        for c in bot.get("commands") or []:
            if c.get("cmd") == first:
                return c.get("function") or default_fn, True, first
        return default_fn, False, None
    return default_fn, False, None


def _session_id(bot_id: str, chat_id: Any) -> str:
    # AgentCore requires runtimeSessionId length >= 33; pad with a hex digest.
    base = f"tg-{bot_id}-{chat_id}"
    pad = hashlib.sha256(base.encode()).hexdigest()
    return (base + "-" + pad)[:64]


def _resolve_gateways(tenant_id: str, gateway_ids: list[str]) -> list[dict]:
    """Look up Gateway items by id; drop anything that isn't ready."""
    out: list[dict] = []
    if not gateway_ids:
        return out
    table = _table()
    for gid in gateway_ids:
        try:
            res = table.get_item(Key={"PK": f"TENANT#{tenant_id}", "SK": f"GATEWAY#{gid}"})
        except Exception:  # noqa: S112 — degrade gracefully; webhook never 5xx
            continue
        item = res.get("Item")
        if not item or item.get("status") != "ready" or not item.get("gatewayUrl"):
            continue
        out.append({"id": gid, "url": item["gatewayUrl"]})
    return out


def _invoke_harness(
    fn: dict,
    text: str,
    bot_id: str,
    chat_id: Any,
    gateways: list[dict] | None = None,
) -> tuple[str, int]:
    if fn.get("type") != "bedrock_harness":
        raise ValueError(f"unsupported function type: {fn.get('type')!r}")
    prompt = (fn.get("promptTemplate") or "{text}").format(text=text)
    payload: dict = {"prompt": prompt}
    if gateways:
        payload["gateways"] = gateways
    kwargs: dict = {
        "agentRuntimeArn": fn["agentRuntimeArn"],
        "runtimeSessionId": _session_id(bot_id, chat_id),
        "payload": json.dumps(payload).encode(),
        "contentType": "application/json",
        "accept": "application/json",
    }
    qualifier = fn.get("qualifier")
    if qualifier:
        kwargs["qualifier"] = qualifier

    t0 = time.time()
    resp = _bedrock().invoke_agent_runtime(**kwargs)
    body = resp["response"].read().decode()
    latency_ms = int((time.time() - t0) * 1000)

    out = body
    try:
        parsed = json.loads(body)
        if isinstance(parsed, dict):
            out = parsed.get("output") or parsed.get("message") or body
        elif isinstance(parsed, str):
            out = parsed
    except json.JSONDecodeError:
        pass
    return out[:4096], latency_ms


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

        fn, matched, matched_cmd = _resolve_function(bot, text)

        sent = False
        reply: str | None = None
        latency_ms: int | None = None

        if not text or chat_id is None:
            _put_event(
                bot_id,
                "webhook.received",
                "(no text or chat)",
                {"trace_id": trace_id, "chat_id": chat_id, "matched": matched},
            )
            return _ok()

        if not fn:
            _put_event(
                bot_id,
                "webhook.no_function",
                "no function configured",
                {
                    "trace_id": trace_id,
                    "chat_id": chat_id,
                    "text": text[:500],
                    "matched": matched,
                    "matched_cmd": matched_cmd,
                },
            )
            _log("webhook.no_function", trace_id=trace_id, bot_id=bot_id)
            return _ok()

        gateways = _resolve_gateways(tenant_id, fn.get("gatewayIds") or [])
        try:
            reply, latency_ms = _invoke_harness(fn, text, bot_id, chat_id, gateways=gateways)
        except Exception as e:
            _log("webhook.harness_failed", trace_id=trace_id, bot_id=bot_id, error=str(e))
            _put_event(
                bot_id,
                "webhook.harness.error",
                f"harness invocation failed: {e}",
                {
                    "trace_id": trace_id,
                    "chat_id": chat_id,
                    "agentRuntimeArn": fn.get("agentRuntimeArn"),
                    "matched_cmd": matched_cmd,
                    "error": str(e),
                },
            )
            return _ok()

        try:
            token = _get_secret(tenant_id, bot["secretId"])
            _send_message(token, chat_id, reply)
            sent = True
        except Exception as e:
            _log("webhook.send_failed", trace_id=trace_id, bot_id=bot_id, error=str(e))
            _put_event(
                bot_id,
                "webhook.error",
                f"sendMessage failed: {e}",
                {"trace_id": trace_id, "agentRuntimeArn": fn.get("agentRuntimeArn")},
            )

        _put_event(
            bot_id,
            "webhook.harness.invoked",
            f"{text[:80]}",
            {
                "trace_id": trace_id,
                "chat_id": chat_id,
                "matched": matched,
                "matched_cmd": matched_cmd,
                "agentRuntimeArn": fn.get("agentRuntimeArn"),
                "gatewayIds": [g["id"] for g in gateways],
                "latencyMs": latency_ms,
                "sent": sent,
                "text": text[:500],
            },
        )
        _log(
            "webhook.ok",
            trace_id=trace_id,
            bot_id=bot_id,
            matched=matched,
            sent=sent,
            harness_latency_ms=latency_ms,
            latency_ms=int((time.time() - start) * 1000),
        )
        return _ok()
    except Exception as e:
        _log("webhook.unhandled", trace_id=trace_id, error=str(e))
        return _ok()  # never 5xx
