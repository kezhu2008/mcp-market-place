from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

PROVISIONED_HARNESS = {
    "agentRuntimeArn": "arn:aws:bedrock-agentcore:ap-southeast-2:668532754740:runtime/h1",
    "agentRuntimeId": "rt_h1",
    "qualifier": None,
}


def _client(aws):
    # Build the app after moto is active.
    from app.main import app

    return TestClient(app)


def _make_harness(client, headers, name: str = "h"):
    with patch(
        "app.services.agentcore_harness.create",
        return_value=PROVISIONED_HARNESS,
    ):
        r = client.post(
            "/harnesses",
            json={
                "name": name,
                "description": "",
                "model": "anthropic.claude-sonnet-4-6",
                "systemPrompt": "you are a helpful assistant",
                "gatewayIds": [],
            },
            headers=headers,
        )
    assert r.status_code == 201, r.text
    return r.json()


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
    assert "value" not in r.json()

    harness = _make_harness(c, headers)

    # Create bot pointing at the platform harness.
    r = c.post(
        "/bots",
        json={
            "name": "ping-bot",
            "description": "",
            "type": "telegram",
            "secretId": secret_id,
            "commands": [{"cmd": "/ping"}],
            "defaultFunction": {"type": "bedrock_harness", "harnessId": harness["id"]},
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    bot = r.json()
    assert bot["status"] == "draft"
    assert bot["defaultFunction"]["harnessId"] == harness["id"]
    assert bot["commands"] == [{"cmd": "/ping", "function": None}]

    with patch("app.services.telegram.set_webhook", new=AsyncMock(return_value={})):
        r = c.post(f"/bots/{bot['id']}/deploy", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "deployed"

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


def test_bot_create_rejects_missing_harness(aws):
    c = _client(aws)
    headers = {"Authorization": "Bearer stub"}

    r = c.post("/secrets", json={"name": "tg", "description": "", "value": "x"}, headers=headers)
    secret_id = r.json()["id"]

    r = c.post(
        "/bots",
        json={
            "name": "b",
            "secretId": secret_id,
            "commands": [],
            "defaultFunction": {"type": "bedrock_harness", "harnessId": "hns_does_not_exist"},
        },
        headers=headers,
    )
    assert r.status_code == 404, r.text


def test_patch_clears_default_function(aws):
    c = _client(aws)
    headers = {"Authorization": "Bearer stub"}

    r = c.post("/secrets", json={"name": "tg", "description": "", "value": "x"}, headers=headers)
    secret_id = r.json()["id"]
    harness = _make_harness(c, headers)

    r = c.post(
        "/bots",
        json={
            "name": "b",
            "secretId": secret_id,
            "commands": [],
            "defaultFunction": {"type": "bedrock_harness", "harnessId": harness["id"]},
        },
        headers=headers,
    )
    bot_id = r.json()["id"]

    r = c.patch(f"/bots/{bot_id}", json={"defaultFunction": None}, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["defaultFunction"] is None


def test_patch_updates_command_function(aws):
    c = _client(aws)
    headers = {"Authorization": "Bearer stub"}

    r = c.post("/secrets", json={"name": "tg", "description": "", "value": "x"}, headers=headers)
    secret_id = r.json()["id"]
    harness = _make_harness(c, headers)

    r = c.post(
        "/bots",
        json={
            "name": "b",
            "secretId": secret_id,
            "commands": [{"cmd": "/start"}],
        },
        headers=headers,
    )
    bot_id = r.json()["id"]

    r = c.patch(
        f"/bots/{bot_id}",
        json={
            "commands": [
                {
                    "cmd": "/start",
                    "function": {"type": "bedrock_harness", "harnessId": harness["id"]},
                }
            ]
        },
        headers=headers,
    )
    assert r.status_code == 200, r.text
    cmds = r.json()["commands"]
    assert cmds[0]["function"]["harnessId"] == harness["id"]


def test_test_function_requires_configured_function(aws):
    c = _client(aws)
    headers = {"Authorization": "Bearer stub"}

    r = c.post("/secrets", json={"name": "tg", "description": "", "value": "x"}, headers=headers)
    secret_id = r.json()["id"]

    r = c.post(
        "/bots",
        json={"name": "b", "secretId": secret_id, "commands": []},
        headers=headers,
    )
    bot_id = r.json()["id"]

    r = c.post(
        f"/bots/{bot_id}/test-function",
        json={"text": "hello", "useDefault": True},
        headers=headers,
    )
    assert r.status_code == 400, r.text


def test_test_function_invokes_harness(aws):
    c = _client(aws)
    headers = {"Authorization": "Bearer stub"}

    r = c.post("/secrets", json={"name": "tg", "description": "", "value": "x"}, headers=headers)
    secret_id = r.json()["id"]
    harness = _make_harness(c, headers)

    r = c.post(
        "/bots",
        json={
            "name": "b",
            "secretId": secret_id,
            "commands": [],
            "defaultFunction": {"type": "bedrock_harness", "harnessId": harness["id"]},
        },
        headers=headers,
    )
    bot_id = r.json()["id"]

    with patch(
        "app.services.bedrock.invoke_harness",
        return_value=("hello back", 123, '{"output": "hello back"}'),
    ) as m:
        r = c.post(
            f"/bots/{bot_id}/test-function",
            json={"text": "hi", "useDefault": True},
            headers=headers,
        )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["output"] == "hello back"
    assert body["latencyMs"] == 123
    assert m.call_count == 1
    # The synthetic fn dict carries the resolved ARN, not the user's harnessId.
    fn = m.call_args.args[0]
    assert fn["agentRuntimeArn"] == PROVISIONED_HARNESS["agentRuntimeArn"]
