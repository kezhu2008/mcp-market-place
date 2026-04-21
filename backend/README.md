# Backend

FastAPI control-plane API, deployed to Lambda via Mangum.

## Local dev

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ruff check .
mypy app
pytest
uvicorn app.main:app --reload --port 8000
```

## Layout

- `app/main.py` — FastAPI app + Mangum handler + CORS + trace middleware
- `app/deps.py` — Cognito JWT verification, tenant resolver
- `app/routers/` — bots, secrets, events, dashboard
- `app/services/dynamo.py` — single-table access layer
- `app/services/secrets_manager.py` — AWS Secrets Manager wrapper (values never logged)
- `app/services/telegram.py` — Telegram Bot API client
- `app/logging.py` — structured JSON logging with automatic redaction

## Env

- `AWS_REGION` (default `ap-southeast-2`)
- `TABLE_NAME`
- `SECRETS_PREFIX` (default `mcp-platform`)
- `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID`
- `WEBHOOK_BASE_URL` — the webhook Lambda Function URL
- `DEFAULT_TENANT_ID` — Phase 1 hardcoded tenant (default `t_default`)

Without Cognito config, the API accepts any bearer token and treats the caller as `local-user` — useful for dev.
