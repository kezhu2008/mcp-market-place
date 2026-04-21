from __future__ import annotations

import json
import os
from unittest.mock import patch

import boto3
import pytest
from moto import mock_aws

os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ["AWS_DEFAULT_REGION"] = "ap-southeast-2"
os.environ["TABLE_NAME"] = "wh_test"
os.environ["SECRETS_PREFIX"] = "mcp-platform-test"


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

        res = boto3.resource("dynamodb", region_name="ap-southeast-2").Table("wh_test")
        res.put_item(
            Item={
                "PK": "TENANT#t_default",
                "SK": "BOT#bot_abc",
                "GSI1PK": "WEBHOOK#wh_path",
                "GSI1SK": "BOT",
                "id": "bot_abc",
                "tenantId": "t_default",
                "status": "deployed",
                "secretId": "sec_1",
                "commands": [{"cmd": "/ping", "template": "pong"}],
                "webhookPath": "wh_path",
            }
        )
        yield


def _event(path: str, body: dict, token: str = "sekret") -> dict:
    return {
        "rawPath": f"/{path}",
        "headers": {"x-telegram-bot-api-secret-token": token},
        "body": json.dumps(body),
    }


def test_ping_matches_and_sends(aws):
    import handler as h

    with patch.object(h, "_send_message") as send:
        res = h.handler(
            _event("wh_path", {"message": {"text": "/ping", "chat": {"id": 42}}}),
            None,
        )
    assert res == {"statusCode": 200, "body": ""}
    send.assert_called_once_with("bot-token-xyz", 42, "pong")


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


def test_non_command_is_swallowed(aws):
    import handler as h

    with patch.object(h, "_send_message") as send:
        res = h.handler(
            _event("wh_path", {"message": {"text": "just saying hi", "chat": {"id": 42}}}),
            None,
        )
    assert res["statusCode"] == 200
    send.assert_not_called()


def test_match_command_handles_bot_suffix():
    import handler as h

    assert h._match_command([{"cmd": "/ping", "template": "pong"}], "/ping@SalesBot") == "pong"
