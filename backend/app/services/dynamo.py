"""Single-table DynamoDB access layer for the MCP Platform.

Schema:
    PK (S) + SK (S)
    GSI1: GSI1PK + GSI1SK  — lookup Bot by webhookPath
    GSI2: GSI2PK + GSI2SK  — list Events for a Bot, time-sorted

Items:
    User    : PK=TENANT#<tid>  SK=USER#<sub>
    Bot     : PK=TENANT#<tid>  SK=BOT#<botId>      GSI1PK=WEBHOOK#<path>  GSI1SK=BOT
    Secret  : PK=TENANT#<tid>  SK=SECRET#<secId>
    Gateway : PK=TENANT#<tid>  SK=GATEWAY#<gwId>
    Event   : PK=BOT#<botId>   SK=EVENT#<ts>#<ulid>  GSI2PK=BOT#<botId>  GSI2SK=EVENT#<ts>
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

from ..config import settings


def _table():
    # Lazy so test fixtures (moto) can intercept before first boto3 call.
    return boto3.resource("dynamodb", region_name=settings.region).Table(settings.table_name)


def _now() -> str:
    return datetime.now(UTC).isoformat()


# ── Bots ────────────────────────────────────────────────────────────
def put_bot(bot: dict[str, Any]) -> None:
    _table().put_item(
        Item={
            "PK": f"TENANT#{bot['tenantId']}",
            "SK": f"BOT#{bot['id']}",
            "GSI1PK": f"WEBHOOK#{bot['webhookPath']}",
            "GSI1SK": "BOT",
            **bot,
        }
    )


def get_bot(tenant_id: str, bot_id: str) -> dict[str, Any] | None:
    res = _table().get_item(Key={"PK": f"TENANT#{tenant_id}", "SK": f"BOT#{bot_id}"})
    return res.get("Item")


def get_bot_by_webhook_path(path: str) -> dict[str, Any] | None:
    res = _table().query(
        IndexName="GSI1",
        KeyConditionExpression=Key("GSI1PK").eq(f"WEBHOOK#{path}") & Key("GSI1SK").eq("BOT"),
        Limit=1,
    )
    items = res.get("Items", [])
    return items[0] if items else None


def list_bots(tenant_id: str) -> list[dict[str, Any]]:
    res = _table().query(
        KeyConditionExpression=Key("PK").eq(f"TENANT#{tenant_id}") & Key("SK").begins_with("BOT#"),
    )
    return res.get("Items", [])


def update_bot(tenant_id: str, bot_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    updates = {**updates, "updatedAt": _now()}
    expr_names = {f"#{k}": k for k in updates}
    expr_values = {f":{k}": v for k, v in updates.items()}
    update_expr = "SET " + ", ".join(f"#{k} = :{k}" for k in updates)
    res = _table().update_item(
        Key={"PK": f"TENANT#{tenant_id}", "SK": f"BOT#{bot_id}"},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
        ReturnValues="ALL_NEW",
    )
    return res["Attributes"]


def delete_bot(tenant_id: str, bot_id: str) -> None:
    _table().delete_item(Key={"PK": f"TENANT#{tenant_id}", "SK": f"BOT#{bot_id}"})


# ── Secrets ─────────────────────────────────────────────────────────
def put_secret_meta(secret: dict[str, Any]) -> None:
    _table().put_item(
        Item={
            "PK": f"TENANT#{secret['tenantId']}",
            "SK": f"SECRET#{secret['id']}",
            **secret,
        }
    )


def get_secret_meta(tenant_id: str, secret_id: str) -> dict[str, Any] | None:
    res = _table().get_item(Key={"PK": f"TENANT#{tenant_id}", "SK": f"SECRET#{secret_id}"})
    return res.get("Item")


def list_secrets(tenant_id: str) -> list[dict[str, Any]]:
    res = _table().query(
        KeyConditionExpression=Key("PK").eq(f"TENANT#{tenant_id}") & Key("SK").begins_with("SECRET#"),
    )
    return res.get("Items", [])


def update_secret_meta(tenant_id: str, secret_id: str, updates: dict[str, Any]) -> None:
    expr_names = {f"#{k}": k for k in updates}
    expr_values = {f":{k}": v for k, v in updates.items()}
    update_expr = "SET " + ", ".join(f"#{k} = :{k}" for k in updates)
    _table().update_item(
        Key={"PK": f"TENANT#{tenant_id}", "SK": f"SECRET#{secret_id}"},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
    )


def delete_secret_meta(tenant_id: str, secret_id: str) -> None:
    _table().delete_item(Key={"PK": f"TENANT#{tenant_id}", "SK": f"SECRET#{secret_id}"})


# ── Gateways ────────────────────────────────────────────────────────
def put_gateway(gw: dict[str, Any]) -> None:
    _table().put_item(
        Item={
            "PK": f"TENANT#{gw['tenantId']}",
            "SK": f"GATEWAY#{gw['id']}",
            **gw,
        }
    )


def get_gateway(tenant_id: str, gw_id: str) -> dict[str, Any] | None:
    res = _table().get_item(Key={"PK": f"TENANT#{tenant_id}", "SK": f"GATEWAY#{gw_id}"})
    return res.get("Item")


def list_gateways(tenant_id: str) -> list[dict[str, Any]]:
    res = _table().query(
        KeyConditionExpression=Key("PK").eq(f"TENANT#{tenant_id}") & Key("SK").begins_with("GATEWAY#"),
    )
    return res.get("Items", [])


def update_gateway(tenant_id: str, gw_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    updates = {**updates, "updatedAt": _now()}
    expr_names = {f"#{k}": k for k in updates}
    expr_values = {f":{k}": v for k, v in updates.items()}
    update_expr = "SET " + ", ".join(f"#{k} = :{k}" for k in updates)
    res = _table().update_item(
        Key={"PK": f"TENANT#{tenant_id}", "SK": f"GATEWAY#{gw_id}"},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
        ReturnValues="ALL_NEW",
    )
    return res["Attributes"]


def delete_gateway(tenant_id: str, gw_id: str) -> None:
    _table().delete_item(Key={"PK": f"TENANT#{tenant_id}", "SK": f"GATEWAY#{gw_id}"})


# ── Events ──────────────────────────────────────────────────────────
def put_event(bot_id: str, event: dict[str, Any]) -> None:
    sk = f"EVENT#{event['ts']}#{event['id']}"
    _table().put_item(
        Item={
            "PK": f"BOT#{bot_id}",
            "SK": sk,
            "GSI2PK": f"BOT#{bot_id}",
            "GSI2SK": f"EVENT#{event['ts']}",
            **event,
            # TTL 30 days
            "ttl": int((datetime.now(UTC).timestamp()) + 30 * 86400),
        }
    )


def list_bot_events(bot_id: str, limit: int = 50) -> list[dict[str, Any]]:
    res = _table().query(
        KeyConditionExpression=Key("PK").eq(f"BOT#{bot_id}") & Key("SK").begins_with("EVENT#"),
        ScanIndexForward=False,
        Limit=limit,
    )
    return res.get("Items", [])
