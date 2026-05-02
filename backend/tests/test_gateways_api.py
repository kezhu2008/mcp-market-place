from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient


def _client(aws):
    from app.main import app

    return TestClient(app)


def _provisioned_gateway():
    return {
        "gatewayArn": "arn:aws:bedrock-agentcore:ap-southeast-2:668532754740:gateway/g1",
        "gatewayUrl": "https://gw.example/mcp/g1",
        "targetId": "tgt_1",
        "credentialProviderArn": (
            "arn:aws:bedrock-agentcore:ap-southeast-2:668532754740:credential-provider/cp1"
        ),
    }


def _provisioned_harness():
    return {
        "agentRuntimeArn": "arn:aws:bedrock-agentcore:ap-southeast-2:668532754740:runtime/h1",
        "agentRuntimeId": "rt_h1",
        "qualifier": None,
    }


def _create_gateway(client, headers, name: str = "g") -> dict:
    with patch(
        "app.services.agentcore_gateway.create",
        return_value=_provisioned_gateway(),
    ):
        r = client.post(
            "/gateways",
            json={"name": name, "description": "", "openapiSpec": "{}", "token": "x"},
            headers=headers,
        )
    assert r.status_code == 201, r.text
    return r.json()


def _create_harness(client, headers, gateway_ids: list[str] | None = None) -> dict:
    with patch(
        "app.services.agentcore_harness.create",
        return_value=_provisioned_harness(),
    ):
        r = client.post(
            "/harnesses",
            json={
                "name": "h",
                "description": "",
                "model": "anthropic.claude-sonnet-4-6",
                "systemPrompt": "",
                "gatewayIds": gateway_ids or [],
            },
            headers=headers,
        )
    assert r.status_code == 201, r.text
    return r.json()


def test_create_gateway_provisions_and_returns_ready(aws):
    c = _client(aws)
    headers = {"Authorization": "Bearer stub"}

    with patch(
        "app.services.agentcore_gateway.create",
        return_value=_provisioned_gateway(),
    ) as m:
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

    gw = _create_gateway(c, headers)

    r = c.get("/gateways", headers=headers)
    assert r.status_code == 200
    assert any(g["id"] == gw["id"] for g in r.json())

    with patch("app.services.agentcore_gateway.destroy") as destroy:
        r = c.delete(f"/gateways/{gw['id']}", headers=headers)
    assert r.status_code == 204
    destroy.assert_called_once()

    r = c.get("/gateways", headers=headers)
    assert all(g["id"] != gw["id"] for g in r.json())


def test_delete_blocked_when_gateway_linked_by_harness(aws):
    c = _client(aws)
    headers = {"Authorization": "Bearer stub"}

    gw = _create_gateway(c, headers)
    hns = _create_harness(c, headers, gateway_ids=[gw["id"]])

    r = c.delete(f"/gateways/{gw['id']}", headers=headers)
    assert r.status_code == 409, r.text
    assert hns["id"] in r.json()["detail"]


def test_test_gateway_returns_tools(aws):
    c = _client(aws)
    headers = {"Authorization": "Bearer stub"}

    gw = _create_gateway(c, headers)

    fake_tools = [
        {"name": "get_account", "description": "fetch account info"},
        {"name": "list_charges", "description": "list charges"},
    ]
    with patch(
        "app.services.agentcore_gateway.list_tools",
        return_value=(fake_tools, 42),
    ) as m:
        r = c.post(f"/gateways/{gw['id']}/test", headers=headers)

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tools"] == fake_tools
    assert body["latencyMs"] == 42
    m.assert_called_once()


def test_test_gateway_blocked_when_not_ready(aws):
    """If a gateway's AWS provisioning failed (status=error), /test should 400."""
    c = _client(aws)
    headers = {"Authorization": "Bearer stub"}

    with patch("app.services.agentcore_gateway.create", side_effect=RuntimeError("fail")):
        c.post(
            "/gateways",
            json={"name": "g", "description": "", "openapiSpec": "{}", "token": "x"},
            headers=headers,
        )

    # Reload list to find the errored gateway.
    items = c.get("/gateways", headers=headers).json()
    gid = items[0]["id"]
    r = c.post(f"/gateways/{gid}/test", headers=headers)
    assert r.status_code == 400, r.text
