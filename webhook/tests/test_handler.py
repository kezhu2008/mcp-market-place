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


VALID_ARN = (
    "arn:aws:bedrock-agentcore:ap-southeast-2:668532754740:runtime/sales-harness"
)
ALT_ARN = (
    "arn:aws:bedrock-agentcore:ap-southeast-2:668532754740:runtime/start-harness"
)


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

        # Default seed: a bot with a /ping command (no override) and a default
        # harness function. Tests can re-put with different commands.
        res = boto3.resource("dynamodb", region_name="ap-southeast-2").Table("wh_test")
        res.put_item(
            Item=_bot_item(
                commands=[{"cmd": "/ping", "function": None}],
                default_function={"type": "bedrock_harness", "agentRuntimeArn": VALID_ARN},
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

    with patch.object(h, "_send_message") as send, \
         patch.object(h, "_bedrock", return_value=bedrock):
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

    aws.put_item(
        Item=_bot_item(
            commands=[
                {
                    "cmd": "/start",
                    "function": {"type": "bedrock_harness", "agentRuntimeArn": ALT_ARN},
                }
            ],
            default_function={"type": "bedrock_harness", "agentRuntimeArn": VALID_ARN},
        )
    )

    bedrock = MagicMock()
    bedrock.invoke_agent_runtime.return_value = _harness_response("hello")

    with patch.object(h, "_send_message"), \
         patch.object(h, "_bedrock", return_value=bedrock):
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

    with patch.object(h, "_send_message") as send, \
         patch.object(h, "_bedrock", return_value=bedrock):
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

    with patch.object(h, "_send_message") as send, \
         patch.object(h, "_bedrock", return_value=bedrock):
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
    with patch.object(h, "_send_message") as send, \
         patch.object(h, "_bedrock", return_value=bedrock):
        res = h.handler(
            _event("wh_path", {"message": {"text": "/ping", "chat": {"id": 1}}}),
            None,
        )

    assert res["statusCode"] == 200
    bedrock.invoke_agent_runtime.assert_not_called()
    send.assert_not_called()


def test_harness_failure_returns_200_and_writes_event(aws):
    import handler as h

    bedrock = MagicMock()
    bedrock.invoke_agent_runtime.side_effect = RuntimeError("boom")

    with patch.object(h, "_send_message") as send, \
         patch.object(h, "_bedrock", return_value=bedrock):
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
                "function": {"type": "bedrock_harness", "agentRuntimeArn": ALT_ARN},
            }
        ],
        default_function={"type": "bedrock_harness", "agentRuntimeArn": VALID_ARN},
    )
    fn, matched, name = h._resolve_function(bot, "/ping@SalesBot")
    assert matched is True
    assert name == "/ping"
    assert fn["agentRuntimeArn"] == ALT_ARN
