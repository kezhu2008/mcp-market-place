from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


def _client(aws):
    # Build the app after moto is active.
    from app.main import app

    return TestClient(app)


def test_health(aws):
    c = _client(aws)
    r = c.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_secret_crud_and_bot_deploy_flow(aws):
    c = _client(aws)
    headers = {"Authorization": "Bearer stub"}

    # Create secret
    r = c.post("/secrets", json={"name": "tg", "description": "", "value": "botTOKEN"}, headers=headers)
    assert r.status_code == 201, r.text
    secret_id = r.json()["id"]
    # Value must not leak
    assert "value" not in r.json()

    # Create bot
    r = c.post(
        "/bots",
        json={
            "name": "ping-bot",
            "description": "",
            "type": "telegram",
            "secretId": secret_id,
            "commands": [{"cmd": "/ping", "template": "pong"}],
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    bot = r.json()
    assert bot["status"] == "draft"

    # Deploy with mocked telegram
    with patch("app.services.telegram.set_webhook", new=AsyncMock(return_value={})):
        r = c.post(f"/bots/{bot['id']}/deploy", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "deployed"

    # Dashboard reflects it
    r = c.get("/dashboard", headers=headers)
    assert r.json()["botsDeployed"] == 1


def test_deploy_failure_flips_to_error(aws):
    from app.services import telegram as tg

    c = _client(aws)
    headers = {"Authorization": "Bearer stub"}

    r = c.post("/secrets", json={"name": "tg", "description": "", "value": "botTOKEN"}, headers=headers)
    secret_id = r.json()["id"]
    r = c.post(
        "/bots",
        json={"name": "b", "secretId": secret_id, "commands": []},
        headers=headers,
    )
    bot_id = r.json()["id"]

    with patch(
        "app.services.telegram.set_webhook",
        new=AsyncMock(side_effect=tg.TelegramError("boom")),
    ):
        r = c.post(f"/bots/{bot_id}/deploy", headers=headers)
    assert r.status_code == 502

    r = c.get(f"/bots/{bot_id}", headers=headers)
    assert r.json()["status"] == "error"
    assert r.json()["lastError"]
