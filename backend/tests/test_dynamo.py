from __future__ import annotations


def test_bot_round_trip(aws):
    # Reload modules so they pick up moto.
    from app.services import dynamo

    bot = {
        "id": "bot_abc",
        "tenantId": "t_default",
        "ownerUserId": "u_1",
        "visibility": "private",
        "priceCents": 0,
        "name": "Test",
        "description": "",
        "type": "telegram",
        "status": "draft",
        "secretId": "sec_1",
        "webhookPath": "wh_123",
        "commands": [],
        "deployedAt": None,
        "lastEventAt": None,
        "lastError": None,
        "requests24h": 0,
        "errors24h": 0,
        "createdAt": "2026-04-21T00:00:00Z",
        "updatedAt": "2026-04-21T00:00:00Z",
    }
    dynamo.put_bot(bot)
    got = dynamo.get_bot("t_default", "bot_abc")
    assert got is not None
    assert got["name"] == "Test"
    by_path = dynamo.get_bot_by_webhook_path("wh_123")
    assert by_path is not None
    assert by_path["id"] == "bot_abc"
    listed = dynamo.list_bots("t_default")
    assert len(listed) == 1


def test_event_order(aws):
    from app.services import dynamo

    for i in range(3):
        dynamo.put_event(
            "bot_x",
            {
                "id": f"ev_{i}",
                "botId": "bot_x",
                "ts": f"2026-04-21T00:00:{i:02d}Z",
                "type": "webhook.received",
                "msg": f"#{i}",
                "actor": "telegram-api",
                "details": {},
            },
        )
    events = dynamo.list_bot_events("bot_x", 10)
    assert [e["msg"] for e in events] == ["#2", "#1", "#0"]
