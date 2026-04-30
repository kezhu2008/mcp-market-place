from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

VALID_ARN = "arn:aws:bedrock-agentcore:ap-southeast-2:668532754740:runtime/sales-harness"


def _client(aws):
    from app.main import app

    return TestClient(app)


def _provisioned():
    return {
        "gatewayArn": "arn:aws:bedrock-agentcore:ap-southeast-2:668532754740:gateway/g1",
        "gatewayUrl": "https://gw.example/mcp/g1",
        "targetId": "tgt_1",
        "credentialProviderArn": (
            "arn:aws:bedrock-agentcore:ap-southeast-2:668532754740:credential-provider/cp1"
        ),
    }


def test_create_gateway_provisions_and_returns_ready(aws):
    c = _client(aws)
    headers = {"Authorization": "Bearer stub"}

    with patch("app.services.agentcore_gateway.create", return_value=_provisioned()) as m:
        r = c.post(
            "/gateways",
            json={
                "name": "stripe",
                "description": "stripe public api",
                "openapiSpec": '{"openapi": "3.0.0", "info": {"title": "stripe"}}',
                "token": "sk_test_xyz",
            },
            headers=headers,
        )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "ready"
    assert body["gatewayUrl"] == "https://gw.example/mcp/g1"
    assert body["secretId"].endswith("/api-token")
    # Token must never appear in the response.
    assert "token" not in body
    assert m.call_count == 1


def test_create_gateway_provisioning_failure_marks_error(aws):
    c = _client(aws)
    headers = {"Authorization": "Bearer stub"}

    with patch("app.services.agentcore_gateway.create", side_effect=RuntimeError("aws boom")):
        r = c.post(
            "/gateways",
            json={
                "name": "stripe",
                "description": "",
                "openapiSpec": "{}",
                "token": "x",
            },
            headers=headers,
        )
    assert r.status_code == 502, r.text


def test_list_and_delete_gateway(aws):
    c = _client(aws)
    headers = {"Authorization": "Bearer stub"}

    with patch("app.services.agentcore_gateway.create", return_value=_provisioned()):
        r = c.post(
            "/gateways",
            json={"name": "g", "description": "", "openapiSpec": "{}", "token": "x"},
            headers=headers,
        )
    gid = r.json()["id"]

    r = c.get("/gateways", headers=headers)
    assert r.status_code == 200
    assert any(g["id"] == gid for g in r.json())

    with patch("app.services.agentcore_gateway.destroy") as destroy:
        r = c.delete(f"/gateways/{gid}", headers=headers)
    assert r.status_code == 204
    destroy.assert_called_once()

    r = c.get("/gateways", headers=headers)
    assert all(g["id"] != gid for g in r.json())


def test_delete_blocked_when_gateway_linked_by_bot(aws):
    c = _client(aws)
    headers = {"Authorization": "Bearer stub"}

    with patch("app.services.agentcore_gateway.create", return_value=_provisioned()):
        gw = c.post(
            "/gateways",
            json={"name": "g", "description": "", "openapiSpec": "{}", "token": "x"},
            headers=headers,
        ).json()

    sec = c.post("/secrets", json={"name": "tg", "description": "", "value": "v"}, headers=headers).json()
    bot = c.post(
        "/bots",
        json={
            "name": "b",
            "secretId": sec["id"],
            "commands": [],
            "defaultFunction": {
                "type": "bedrock_harness",
                "agentRuntimeArn": VALID_ARN,
                "gatewayIds": [gw["id"]],
            },
        },
        headers=headers,
    ).json()

    r = c.delete(f"/gateways/{gw['id']}", headers=headers)
    assert r.status_code == 409, r.text
    assert bot["id"] in r.json()["detail"]


def test_test_function_passes_gateways_to_invoke(aws):
    c = _client(aws)
    headers = {"Authorization": "Bearer stub"}

    with patch("app.services.agentcore_gateway.create", return_value=_provisioned()):
        gw = c.post(
            "/gateways",
            json={"name": "g", "description": "", "openapiSpec": "{}", "token": "x"},
            headers=headers,
        ).json()

    sec = c.post("/secrets", json={"name": "tg", "description": "", "value": "v"}, headers=headers).json()
    bot = c.post(
        "/bots",
        json={
            "name": "b",
            "secretId": sec["id"],
            "commands": [],
            "defaultFunction": {
                "type": "bedrock_harness",
                "agentRuntimeArn": VALID_ARN,
                "gatewayIds": [gw["id"]],
            },
        },
        headers=headers,
    ).json()

    with patch(
        "app.services.bedrock.invoke_harness",
        return_value=("ok", 10, '{"output":"ok"}'),
    ) as m:
        r = c.post(
            f"/bots/{bot['id']}/test-function",
            json={"text": "hi", "useDefault": True},
            headers=headers,
        )

    assert r.status_code == 200, r.text
    kwargs = m.call_args.kwargs
    assert kwargs["gateways"] == [{"id": gw["id"], "url": "https://gw.example/mcp/g1"}]
