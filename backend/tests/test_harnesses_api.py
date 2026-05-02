from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

PROVISIONED = {
    "agentRuntimeArn": "arn:aws:bedrock-agentcore:ap-southeast-2:668532754740:runtime/h1",
    "agentRuntimeId": "rt_h1",
    "qualifier": None,
}


def _client(aws):
    from app.main import app

    return TestClient(app)


def _create_harness(client, headers, gateway_ids: list[str] | None = None, name: str = "h") -> dict:
    with patch("app.services.agentcore_harness.create", return_value=PROVISIONED):
        r = client.post(
            "/harnesses",
            json={
                "name": name,
                "description": "",
                "model": "anthropic.claude-sonnet-4-6",
                "systemPrompt": "you are kind",
                "gatewayIds": gateway_ids or [],
            },
            headers=headers,
        )
    assert r.status_code == 201, r.text
    return r.json()


def _create_gateway(client, headers) -> dict:
    arn_root = "arn:aws:bedrock-agentcore:ap-southeast-2:668532754740"
    with patch(
        "app.services.agentcore_gateway.create",
        return_value={
            "gatewayArn": f"{arn_root}:gateway/g1",
            "gatewayUrl": "https://gw.example/mcp/g1",
            "targetId": "tgt_1",
            "credentialProviderArn": f"{arn_root}:credential-provider/cp1",
        },
    ):
        r = client.post(
            "/gateways",
            json={"name": "g", "description": "", "openapiSpec": "{}", "token": "x"},
            headers=headers,
        )
    assert r.status_code == 201, r.text
    return r.json()


def test_create_harness_provisions_and_returns_ready(aws):
    c = _client(aws)
    headers = {"Authorization": "Bearer stub"}

    hns = _create_harness(c, headers)
    assert hns["status"] == "ready"
    assert hns["agentRuntimeArn"] == PROVISIONED["agentRuntimeArn"]
    assert hns["model"] == "anthropic.claude-sonnet-4-6"
    assert hns["systemPrompt"] == "you are kind"


def test_create_harness_failure_marks_error(aws):
    c = _client(aws)
    headers = {"Authorization": "Bearer stub"}

    with patch("app.services.agentcore_harness.create", side_effect=RuntimeError("aws boom")):
        r = c.post(
            "/harnesses",
            json={
                "name": "h",
                "model": "anthropic.claude-sonnet-4-6",
                "systemPrompt": "",
                "gatewayIds": [],
            },
            headers=headers,
        )
    assert r.status_code == 502, r.text


def test_list_get_delete_harness(aws):
    c = _client(aws)
    headers = {"Authorization": "Bearer stub"}

    hns = _create_harness(c, headers)

    r = c.get("/harnesses", headers=headers)
    assert any(h["id"] == hns["id"] for h in r.json())

    r = c.get(f"/harnesses/{hns['id']}", headers=headers)
    assert r.status_code == 200

    with patch("app.services.agentcore_harness.destroy") as destroy:
        r = c.delete(f"/harnesses/{hns['id']}", headers=headers)
    assert r.status_code == 204
    destroy.assert_called_once()

    r = c.get(f"/harnesses/{hns['id']}", headers=headers)
    assert r.status_code == 404


def test_delete_blocked_when_referenced_by_bot(aws):
    c = _client(aws)
    headers = {"Authorization": "Bearer stub"}

    hns = _create_harness(c, headers)

    sec = c.post("/secrets", json={"name": "tg", "description": "", "value": "v"}, headers=headers).json()
    bot = c.post(
        "/bots",
        json={
            "name": "b",
            "secretId": sec["id"],
            "commands": [],
            "defaultFunction": {"type": "bedrock_harness", "harnessId": hns["id"]},
        },
        headers=headers,
    ).json()

    r = c.delete(f"/harnesses/{hns['id']}", headers=headers)
    assert r.status_code == 409, r.text
    assert bot["id"] in r.json()["detail"]


def test_test_harness_invokes(aws):
    c = _client(aws)
    headers = {"Authorization": "Bearer stub"}

    gw = _create_gateway(c, headers)
    hns = _create_harness(c, headers, gateway_ids=[gw["id"]])

    with patch(
        "app.services.bedrock.invoke_harness",
        return_value=("hi back", 7, '{"output":"hi back"}'),
    ) as m:
        r = c.post(f"/harnesses/{hns['id']}/test", json={"text": "hi"}, headers=headers)

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["output"] == "hi back"
    assert body["latencyMs"] == 7
    # The synthetic fn passed in carries the resolved AgentCore ARN, plus the
    # gateways list resolved through the harness.
    fn_arg = m.call_args.args[0]
    assert fn_arg["agentRuntimeArn"] == PROVISIONED["agentRuntimeArn"]
    kwargs = m.call_args.kwargs
    assert kwargs["gateways"] == [{"id": gw["id"], "url": "https://gw.example/mcp/g1"}]


def test_patch_harness_gateways(aws):
    c = _client(aws)
    headers = {"Authorization": "Bearer stub"}

    hns = _create_harness(c, headers)
    gw = _create_gateway(c, headers)

    r = c.patch(
        f"/harnesses/{hns['id']}",
        json={"gatewayIds": [gw["id"]]},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["gatewayIds"] == [gw["id"]]
