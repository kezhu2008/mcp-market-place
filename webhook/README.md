# Webhook Lambda

Isolated hot path for Telegram webhooks.

Exposed via a Lambda Function URL (`AuthType=NONE`). Telegram POSTs to `<base>/<webhookPath>`.

Per invocation:
1. Parse the raw path → bot webhookPath.
2. Query DynamoDB GSI1 → bot config (status, commands, secretId).
3. Verify `X-Telegram-Bot-Api-Secret-Token` header.
4. Match first word of message text against `bot.commands`. Send template via `sendMessage`.
5. Write a trimmed `webhook.received` event (max 500 char text, no full payload).
6. Always return `200` (Telegram retries aggressively on 5xx).

## Local

```bash
cd webhook
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Only uses the stdlib `urllib` for outbound HTTP — keeps the Lambda package tiny (boto3 is pre-provided by the AWS runtime).
