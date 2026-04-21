"""Telegram Bot API client — setWebhook, deleteWebhook, sendMessage."""

from __future__ import annotations

import httpx

API = "https://api.telegram.org"


class TelegramError(Exception):
    pass


async def _call(method: str, token: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.post(f"{API}/bot{token}/{method}", json=payload)
    data = res.json()
    if not data.get("ok"):
        raise TelegramError(data.get("description", f"telegram {method} failed"))
    return data.get("result", {})


async def set_webhook(token: str, url: str, secret_token: str) -> dict:
    return await _call(
        "setWebhook",
        token,
        {
            "url": url,
            "secret_token": secret_token,
            "allowed_updates": ["message"],
            "drop_pending_updates": True,
        },
    )


async def delete_webhook(token: str) -> dict:
    return await _call("deleteWebhook", token, {"drop_pending_updates": False})


async def send_message(token: str, chat_id: int | str, text: str) -> dict:
    return await _call("sendMessage", token, {"chat_id": chat_id, "text": text})
