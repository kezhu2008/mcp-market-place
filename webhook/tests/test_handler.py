from __future__ import annotations

import json
import os
from io import BytesIO
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ["AWS_DEFAULT_REGION"] = "ap-southeast-2"
os.environ["TABLE_NAME"] = "wh_test"
os.environ["SECRETS_PREFIX"] = "mcp-platform-test"


VALID_ARN = "arn:aws:bedrock-agentcore:ap-southeast-2:668532754740:runtime/sales-harness"
ALT_ARN = "arn:aws:bedrock-agentcore:ap-southeast-2:668532754740:runtime/start-harness"


def _bot_item(commands, default_function):
    return {
        "PK": "TENANT#t_default",
        "SK": "BOT#bot_abc",
        "GSI1PK": "WEBHOOK#wh_path",
        "GSI1SK": "BOT",
        "id": "bot_abc",
        "tenantId": "t_default",
        "status": "deployed",
        "secretId": "sec_1",
        "commands": commands,
        "defaultFunction": default_function,
        "webhookPath": "wh_path",
    }


def _harness_item(harness_id: str, agent_runtime_arn: str, gateway_ids=None, status="ready"):
    return {
        "PK": "TENANT#t_default",
        "SK": f"HARNESS#{harness_id}",
        "id": harness_id,
        "tenantId": "t_default",
        "name": harness_id,
        "model": "anthropic.claude-sonnet-4-6",
        "systemPrompt": "",
        "status": status,
        "agentRuntimeArn": agent_runtime_arn,
        "agentRuntimeId": "rt_" + harness_id,
        "gatewayIds": gateway_ids or [],
    }


@pytest.fixture()
def aws():
    with mock_aws():
        ddb = boto3.client("dynamodb", region_name="ap-southeast-2")
        ddb.create_table(
            TableName="wh_test",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "GSI1PK", "AttributeType": "S"},
                {"AttributeName": "GSI1SK", "AttributeType": "S"},
                {"AttributeName": "GSI2PK", "AttributeType": "S"},
                {"AttributeName": "GSI2SK", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "GSI1",
                    "KeySchema": [
                        {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "GSI2",
                    "KeySchema": [
                        {"AttributeName": "GSI2PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI2SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        sm = boto3.client("secretsmanager", region_name="ap-southeast-2")
        sm.create_secret(Name="mcp-platform-test/t_default/sec_1", SecretString="bot-token-xyz")
        sm.create_secret(
            Name="mcp-platform-test/t_default/bot_abc/webhook-secret",
            SecretString="sekret",
        )

        # Default seed: a default-harness Harness item, plus a bot whose
        # defaultFunction points at it. Tests can re-put with different
        # commands / harness configurations.
        res = boto3.resource("dynamodb", region_name="ap-southeast-2").Table("wh_test")
        res.put_item(Item=_harness_item("hns_default", VALID_ARN))
        res.put_item(
            Item=_bot_item(
                commands=[{"cmd": "/ping", "function": None}],
                default_function={"type": "bedrock_harness", "harnessId": "hns_default"},
            )
        )
        yield res


def _event(path: str, body: dict, token: str = "sekret") -> dict:
    return {
        "rawPath": f"/{path}",
        "headers": {"x-telegram-bot-api-secret-token": token},
        "body": json.dumps(body),
    }


def _harness_response(text: str = "pong") -> dict:
    return {"response": BytesIO(json.dumps({"output": text}).encode())}


def test_slash_command_invokes_default_harness(aws):
    import handler as h

    bedrock = MagicMock()
    bedrock.invoke_agent_runtime.return_value = _harness_response("pong")

    with patch.object(h, "_send_message") as send, patch.object(h, "_bedrock", return_value=bedrock):
        res = h.handler(
            _event("wh_path", {"message": {"text": "/ping", "chat": {"id": 42}}}),
            None,
        )

    assert res == {"statusCode": 200, "body": ""}
    send.assert_called_once_with("bot-token-xyz", 42, "pong")
    call = bedrock.invoke_agent_runtime.call_args.kwargs
    assert call["agentRuntimeArn"] == VALID_ARN
    payload = json.loads(call["payload"])
    assert payload == {"prompt": "/ping"}
    assert len(call["runtimeSessionId"]) >= 33


def test_command_function_overrides_default(aws):
    import handler as h

    aws.put_item(Item=_harness_item("hns_alt", ALT_ARN))
    aws.put_item(
        Item=_bot_item(
            commands=[
                {
                    "cmd": "/start",
                    "function": {"type": "bedrock_harness", "harnessId": "hns_alt"},
                }
            ],
            default_function={"type": "bedrock_harness", "harnessId": "hns_default"},
        )
    )

    bedrock = MagicMock()
    bedrock.invoke_agent_runtime.return_value = _harness_response("hello")

    with patch.object(h, "_send_message"), patch.object(h, "_bedrock", return_value=bedrock):
        h.handler(
            _event("wh_path", {"message": {"text": "/start", "chat": {"id": 1}}}),
            None,
        )

    call = bedrock.invoke_agent_runtime.call_args.kwargs
    assert call["agentRuntimeArn"] == ALT_ARN


def test_non_slash_uses_default_function(aws):
    import handler as h

    bedrock = MagicMock()
    bedrock.invoke_agent_runtime.return_value = _harness_response("hi there")

    with patch.object(h, "_send_message") as send, patch.object(h, "_bedrock", return_value=bedrock):
        h.handler(
            _event("wh_path", {"message": {"text": "just saying hi", "chat": {"id": 7}}}),
            None,
        )

    bedrock.invoke_agent_runtime.assert_called_once()
    send.assert_called_once_with("bot-token-xyz", 7, "hi there")


def test_unknown_slash_falls_to_default(aws):
    import handler as h

    bedrock = MagicMock()
    bedrock.invoke_agent_runtime.return_value = _harness_response("idk")

    with patch.object(h, "_send_message") as send, patch.object(h, "_bedrock", return_value=bedrock):
        h.handler(
            _event("wh_path", {"message": {"text": "/unknown arg", "chat": {"id": 1}}}),
            None,
        )

    bedrock.invoke_agent_runtime.assert_called_once()
    send.assert_called_once()


def test_no_function_writes_event_and_skips_send(aws):
    import handler as h

    aws.put_item(
        Item=_bot_item(
            commands=[{"cmd": "/ping", "function": None}],
            default_function=None,
        )
    )

    bedrock = MagicMock()
    with patch.object(h, "_send_message") as send, patch.object(h, "_bedrock", return_value=bedrock):
        res = h.handler(
            _event("wh_path", {"message": {"text": "/ping", "chat": {"id": 1}}}),
            None,
        )

    assert res["statusCode"] == 200
    bedrock.invoke_agent_runtime.assert_not_called()
    send.assert_not_called()


def test_harness_not_found(aws):
    """Bot points at a harnessId that doesn't exist as a Harness item."""
    import handler as h

    aws.put_item(
        Item=_bot_item(
            commands=[],
            default_function={"type": "bedrock_harness", "harnessId": "hns_missing"},
        )
    )

    bedrock = MagicMock()
    with patch.object(h, "_send_message") as send, patch.object(h, "_bedrock", return_value=bedrock):
        res = h.handler(
            _event("wh_path", {"message": {"text": "hi", "chat": {"id": 1}}}),
            None,
        )

    assert res["statusCode"] == 200
    bedrock.invoke_agent_runtime.assert_not_called()
    send.assert_not_called()


def test_harness_not_ready(aws):
    """Harness exists but status != ready (e.g., still provisioning)."""
    import handler as h

    aws.put_item(Item=_harness_item("hns_wip", VALID_ARN, status="creating"))
    aws.put_item(
        Item=_bot_item(
            commands=[],
            default_function={"type": "bedrock_harness", "harnessId": "hns_wip"},
        )
    )

    bedrock = MagicMock()
    with patch.object(h, "_send_message") as send, patch.object(h, "_bedrock", return_value=bedrock):
        res = h.handler(
            _event("wh_path", {"message": {"text": "hi", "chat": {"id": 1}}}),
            None,
        )

    assert res["statusCode"] == 200
    bedrock.invoke_agent_runtime.assert_not_called()
    send.assert_not_called()


def test_harness_invocation_failure_returns_200(aws):
    import handler as h

    bedrock = MagicMock()
    bedrock.invoke_agent_runtime.side_effect = RuntimeError("boom")

    with patch.object(h, "_send_message") as send, patch.object(h, "_bedrock", return_value=bedrock):
        res = h.handler(
            _event("wh_path", {"message": {"text": "/ping", "chat": {"id": 1}}}),
            None,
        )

    assert res["statusCode"] == 200
    send.assert_not_called()


def test_bad_secret_rejected(aws):
    import handler as h

    with patch.object(h, "_send_message") as send:
        res = h.handler(
            _event("wh_path", {"message": {"text": "/ping", "chat": {"id": 1}}}, token="wrong"),
            None,
        )
    assert res["statusCode"] == 200
    send.assert_not_called()


def test_unknown_path_returns_200(aws):
    import handler as h

    res = h.handler(_event("nope", {"message": {"text": "hi"}}), None)
    assert res["statusCode"] == 200


def test_resolve_handles_bot_suffix(aws):
    import handler as h

    bot = _bot_item(
        commands=[
            {
                "cmd": "/ping",
                "function": {"type": "bedrock_harness", "harnessId": "hns_alt"},
            }
        ],
        default_function={"type": "bedrock_harness", "harnessId": "hns_default"},
    )
    fn, matched, name = h._resolve_function(bot, "/ping@SalesBot")
    assert matched is True
    assert name == "/ping"
    assert fn["harnessId"] == "hns_alt"


def test_gateway_urls_passed_in_payload(aws):
    """Harness's linked gateways flow into the invoke payload."""
    import handler as h

    aws.put_item(
        Item={
            "PK": "TENANT#t_default",
            "SK": "GATEWAY#gw_one",
            "id": "gw_one",
            "tenantId": "t_default",
            "name": "stripe",
            "status": "ready",
            "gatewayUrl": "https://gw.example/mcp/one",
        }
    )
    aws.put_item(
        Item={
            "PK": "TENANT#t_default",
            "SK": "GATEWAY#gw_creating",
            "id": "gw_creating",
            "tenantId": "t_default",
            "name": "wip",
            "status": "creating",
            "gatewayUrl": None,
        }
    )
    aws.put_item(
        Item=_harness_item(
            "hns_with_gw",
            VALID_ARN,
            gateway_ids=["gw_one", "gw_creating", "gw_missing"],
        )
    )
    aws.put_item(
        Item=_bot_item(
            commands=[{"cmd": "/ping", "function": None}],
            default_function={"type": "bedrock_harness", "harnessId": "hns_with_gw"},
        )
    )

    bedrock = MagicMock()
    bedrock.invoke_agent_runtime.return_value = _harness_response("hi")

    with patch.object(h, "_send_message"), patch.object(h, "_bedrock", return_value=bedrock):
        h.handler(_event("wh_path", {"message": {"text": "/ping", "chat": {"id": 1}}}), None)

    payload = json.loads(bedrock.invoke_agent_runtime.call_args.kwargs["payload"])
    # Only the ready gateway is forwarded; creating + missing are dropped.
    assert payload["gateways"] == [{"id": "gw_one", "url": "https://gw.example/mcp/one"}]
