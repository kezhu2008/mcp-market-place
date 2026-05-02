# AGENTS.md

Operational notes for AI agents (Claude Code et al.) working on this repo. Non-obvious decisions, gotchas, and the workflow the human collaborator expects. Keep terse.

## Workflow

- **Default branching**: open a feature branch (`claude/<short-slug>`), push, open a PR via `gh pr create`, wait for `pr.yml` CI to go green, **squash-merge + delete branch automatically** (the human said "always merge, don't wait for me"). Don't bypass CI hooks.
- **Direct pushes to `main`**: avoid except for the original deploy-fix saga (Apr 21–28). Going forward: PR-flow.
- **Commit messages**: explain *why*, not *what*. Reference prior PRs / commits when fixing earlier mistakes.
- **Secrets in chat**: the human has pasted AWS access keys in chat at least once. They're permanently in the transcript. After any such paste, remind them to rotate.

## Architecture

| Component | Where | URL / ID |
|---|---|---|
| Frontend (Next.js SSR) | AWS Amplify Hosting | `https://main.d30245m5kpo4p6.amplifyapp.com` (app id `d30245m5kpo4p6`) |
| Backend API | API Gateway HTTP API + Lambda | `https://6sxry3qxgb.execute-api.ap-southeast-2.amazonaws.com/` |
| Webhook ingest | Lambda function URL | `https://ejwk42fttwhrw3fnjrhbpzjcdy0cmfph.lambda-url.ap-southeast-2.on.aws/` |
| Auth | Cognito user pool | `ap-southeast-2_jBwJtjPGl` |
| Cognito hosted UI | | `mcp-platform-prod.auth.ap-southeast-2.amazoncognito.com` |
| DynamoDB | | table `mcp-platform_prod` |
| Region | | `ap-southeast-2` (Sydney) |
| AWS account | | `668532754740` |

Push to `main` → `.github/workflows/deploy.yml` → `terragrunt apply` (state in `s3://mcp-platform-tfstate-668532754740`, lock in `mcp-platform-tflock`) → Amplify auto-build via webhook on the same push.

## Required GitHub secrets

| Secret | Purpose | Notes |
|---|---|---|
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | Deploy IAM user | Long-lived; rotate quarterly |
| `TF_STATE_BUCKET` | terraform state backend | `mcp-platform-tfstate-668532754740` |
| `TF_LOCK_TABLE` | terraform lock table | `mcp-platform-tflock` |
| `ADMIN_EMAIL` | seeded into Cognito as the admin user | |
| `AMPLIFY_GH_TOKEN` | **Classic PAT only** (`ghp_…`), with `repo` + `admin:repo_hook` scopes. Fine-grained PATs (`github_pat_…`) silently fail in `aws_amplify_app.access_token`. |

## Bootstrap (one-time, manual)

`infra/bootstrap/` creates the terraform state bucket + lock table. Run once per AWS account from a workstation with admin AWS creds (NOT from CI — the deploy IAM user that CI uses is created **after** bootstrap and has narrower perms). See `infra/bootstrap/README.md`.

## Bot routing & functions

Each bot routes incoming Telegram messages to a `BotFunction` (today the only variant is `bedrock_harness`, holding a `harnessId` referencing a platform-managed Harness item, plus an optional `promptTemplate`). There are no static `template` replies — every reply is a harness invocation.

Routing precedence (mirrors `_resolve_function` in `webhook/handler.py`):

1. text starts with `/` and matches `commands[*].cmd` and that command has `function` set → invoke `command.function`
2. text starts with `/` and matches a command with `function == null` → invoke `bot.defaultFunction`
3. text starts with `/` but no command matches → invoke `bot.defaultFunction`
4. text doesn't start with `/` → invoke `bot.defaultFunction`
5. resolved function is `null` → no reply, write a `webhook.no_function` event, return 200

Notes for next agents:

- `BotCommand.function = null` means *inherit* `Bot.defaultFunction` at runtime; the inheritance is webhook-side, not stored. PATCHing a bot with `{"defaultFunction": null}` clears it; omitting the key leaves it unchanged (relies on `model_dump(exclude_unset=True)` in `routers/bots.py`).
- A function carries only `harnessId`; the runtime ARN, qualifier, and linked gateway URLs are resolved at invoke time via the Harness item. The webhook does 1 (Bot) + 1 (Harness) + N (Gateway) DDB GetItems per Telegram message — fine for Phase 1 traffic; future optimization is to denormalize the ARN onto the function as a cache.
- **Existing bots configured with raw `agentRuntimeArn` no longer resolve** after this change — there's no migration script. Single-tenant Phase 1; just edit each bot to point at a platform Harness.
- AgentCore IAM: both webhook and backend lambda roles have `bedrock-agentcore:InvokeAgentRuntime` on `arn:aws:bedrock-agentcore:*:*:runtime/*` (wildcards because operator may grant cross-account access via the harness's resource policy). Lambda timeouts are 60s on both. If you see Telegram retries, check CloudWatch for harness latency before assuming a bug.
- Webhook still **never returns 5xx** — harness failures (including not-found / not-ready) write a `webhook.harness.error` event with a `details.reason` field and return 200. Do not change this; Telegram retries aggressively on 5xx and amplifies cost/latency.
- `runtimeSessionId` is derived deterministically as `tg-{botId}-{chatId}` plus a SHA-256 pad (AgentCore minimum length is 33). No DDB session store — conversational memory is the harness's responsibility.
- `POST /bots/{id}/test-function` and `POST /harnesses/{id}/test` both go through `services.bedrock.resolve_harness` + `services.bedrock.invoke_harness`. Removing either endpoint won't simplify the bedrock module.
- The wizard at `app/(app)/bots/new/page.tsx` collects exactly one harness from a dropdown (the bot's `defaultFunction`). Per-command overrides happen on the bot detail page Configuration tab — keep it that way; harness picking during onboarding is one click, custom config hurts conversion.

## Harnesses (AgentCore Runtime)

A `Harness` is a tenant-scoped AgentCore Runtime provisioned by us. Lives at `PK=TENANT#<tid>` / `SK=HARNESS#<id>`. Each Harness is the deployed agent container with a model + system prompt + linked gateways (the gateways are *tools*, not part of the runtime). Bots reference Harnesses by `harnessId`; Harnesses reference Gateways by `gatewayIds`.

Provisioning sequence on `POST /harnesses`:

1. Validate every `gatewayIds[i]` exists for this tenant.
2. DDB-put with `status=creating`.
3. Call `bedrock-agentcore-control:CreateAgentRuntime` with:
   - `agentRuntimeArtifact.containerConfiguration.containerUri = settings.platform_harness_image_uri`
   - `roleArn = settings.platform_harness_role_arn`
   - `environmentVariables = {MODEL_ID, SYSTEM_PROMPT}`
4. DDB-update with `status=ready`, `agentRuntimeArn`, `agentRuntimeId`, `qualifier`.

**Container contract** (anyone swapping `PLATFORM_HARNESS_IMAGE_URI` must honor it):

- Read `MODEL_ID` and `SYSTEM_PROMPT` from environment variables at startup.
- Accept invoke-payload `{prompt, gateways: [{id, url}]}` on each request and connect to listed gateways as MCP servers.

Required env vars on the backend lambda (set in `infra/envs/<env>/main.tf`):

- `PLATFORM_HARNESS_IMAGE_URI` — container image AgentCore pulls when `CreateAgentRuntime` runs. **Auto-built** by `.github/workflows/deploy.yml` from `harness/Dockerfile` (a minimal Python container using the `bedrock-agentcore` SDK + Bedrock `converse`); pushed to a private ECR repo provisioned by `infra/modules/ecr`; tagged with the commit SHA. Override `var.platform_harness_image_uri` to pin to an external image instead.
- `PLATFORM_HARNESS_ROLE_ARN` — IAM role the AgentCore runtime assumes. **Auto-provisioned** by `infra/modules/harness-runtime-role` when `var.platform_harness_role_arn` is unset (the default). Override the variable to point at an operator-managed role. The auto-provisioned role grants `bedrock:InvokeModel*` on `foundation-model/*`, `bedrock-agentcore:InvokeMCPTool` on `gateway/*`, and CloudWatch logs.

Harness image build + deploy flow:

1. CI checkout, set up QEMU + buildx (AgentCore requires `linux/arm64`; runners are amd64).
2. `terragrunt apply` provisions the ECR repo + sets the lambda env to `<repo_url>:<commit_sha>`.
3. CI logs into ECR, runs `docker buildx build --platform linux/arm64`, tags with both `<commit_sha>` and `latest`, pushes.
4. Operators creating a harness via the UI now have a real image to pull. Existing harnesses keep their image (the URI is captured at `CreateAgentRuntime` time).

Brief race window: between step 2 and step 3 the lambda env points at an image that doesn't exist yet. For Phase 1 / single-tenant traffic this is acceptable. Future tightening: build + push first, then apply. Requires the ECR repo to exist out-of-band.

The ECR repo policy (`infra/modules/ecr`) grants pull access to the `bedrock-agentcore.amazonaws.com` service principal; without that, `CreateAgentRuntime` fails with an unauthorized-pull error even though the image exists.

v1 harness image (`harness/app.py`) reads `MODEL_ID` + `SYSTEM_PROMPT` from env, calls Bedrock `converse`, and ignores `payload.gateways`. MCP gateway tool wiring is a follow-up.

Mutability rules:

- `gatewayIds` mutable via `PATCH /harnesses/{id}` (DDB-only, no AWS round-trip — the webhook resolves URLs at invoke time).
- `model` and `systemPrompt` are immutable in v1. They live as runtime env vars baked at `CreateAgentRuntime`; changing them needs `UpdateAgentRuntime`, which is out of scope. Delete + recreate.

Delete cascade rules:

- `DELETE /harnesses/{id}` is **409-blocked** by any bot whose `defaultFunction` or `commands[*].function` references it.
- `DELETE /gateways/{id}` is **409-blocked** by any harness whose `gatewayIds` references it. (Bots reference gateways only transitively through a Harness.)

Gotchas:

- `bedrock-agentcore-control:CreateAgentRuntime` field names are best-effort against a firming-up API. If a real apply surfaces `ValidationException`, adjust `services/agentcore_harness.py` only — nothing else sees the AWS shape.
- The webhook lambda does **NOT** need `bedrock-agentcore-control:*` perms — it only reads Harness items via `dynamodb:GetItem`. Only the backend lambda creates/destroys harnesses.
- `iam:PassRole` is granted to the backend role on `var.platform_harness_role_arn` (or a placeholder when unset). Don't widen this to `*` — it's a cross-account credential-laundering primitive.
- `POST /harnesses/{id}/test` lets operators validate a harness from the UI without touching a bot. It writes no event (vs `POST /bots/{id}/test-function` which writes `function.tested`).

## Gateways (AgentCore Gateway)

A `Gateway` is a tenant-scoped AgentCore Gateway provisioned by us from an OpenAPI spec + an upstream API token. Lives at `PK=TENANT#<tid>` / `SK=GATEWAY#<id>`. The backend calls **three** control-plane APIs in order during `POST /gateways`:

1. `bedrock-agentcore-control:CreateApiKeyCredentialProvider` — stores the user-supplied token as a credential. Token is also stored in our Secrets Manager under `mcp-platform/<tid>/<gwId>/api-token` so it can be rotated symmetrically with bot tokens.
2. `bedrock-agentcore-control:CreateGateway` — creates the MCP-protocol gateway. Inbound auth defaults to `AWS_IAM` so the harness's runtime role authenticates; switch to JWT out-of-band if needed.
3. `bedrock-agentcore-control:CreateGatewayTarget` — wires the OpenAPI spec inline and binds the credential provider.

If any step fails, `services/agentcore_gateway.create` rolls back the partial AWS state before re-raising. The Gateway item flips to `status: error` with `lastError` populated.

**Linking to a harness**: `Harness.gatewayIds` lists Gateway IDs the harness has access to as MCP tools. At invoke time the webhook reads the Harness's `gatewayIds`, fetches each Gateway item, and forwards `{"gateways": [{id, url}]}` in the AgentCore invoke payload. The container is responsible for connecting to those URLs as MCP servers — it's *our* convention, not AgentCore's. Non-ready gateways are silently dropped so a half-provisioned tool doesn't break replies.

`POST /gateways/{id}/test` lets operators validate a deployed gateway from the UI: SigV4-signs an MCP `tools/list` JSON-RPC request to the gateway URL and returns the tool inventory. Confirms reachability, IAM auth, and OpenAPI-to-MCP translation in one round-trip.

**Gotchas:**

- AgentCore control-plane field names (`apiKey`, `protocolType`, `authorizerType`, `targetConfiguration.mcp.openApiSchema.inlinePayload`, `credentialProviderConfigurations`) are best-effort against the firming-up API; if a real `apply` surfaces `ValidationException`, adjust kwargs in `services/agentcore_gateway.py` — nothing else in the codebase depends on the AWS shape.
- Deleting a Gateway is blocked (409) when any **harness** references it (bots reference gateways only transitively through a harness). Unlink in the harness's `gatewayIds` first, then delete.
- The webhook lambda **does NOT** need `bedrock-agentcore-control:*` perms — it only reads Gateway items from DDB (already covered by the existing `dynamodb:GetItem` grant). Only the backend lambda creates/destroys gateways.
- OpenAPI specs are stored inline on the Gateway item (capped at 200 KB to fit DDB single-table item budgets). For very large specs, refactor to S3 + reference, not in scope yet.
- The `/test` endpoint expects a JSON-RPC envelope `{result: {tools: [...]}}` from the gateway. If the AgentCore data plane shape diverges, adjust `agentcore_gateway.list_tools` only.

## Gotchas / lessons

### Amplify Hosting (Next.js SSR)

- **Don't try to manage `iam_service_role_arn` from terraform.** Amplify's internal SSR validator silently rejects terraform-attached roles even when trust policy + permissions are correct (see [Uncommon Engineer write-up](https://www.uncommonengineer.com/docs/engineer/AWS/amplify-ssr-iam-debugging/)). The fix in `infra/modules/amplify/main.tf` is: omit `iam_service_role_arn` and add `lifecycle { ignore_changes = [iam_service_role_arn] }`. Amplify auto-creates a working role on first build.
- **`platform = "WEB_COMPUTE"`** is required for Next.js SSR. Default `WEB` is for static.
- **Monorepo (pnpm workspace)** requires:
  - `AMPLIFY_MONOREPO_APP_ROOT=frontend` env var (set in `infra/envs/prod/main.tf`)
  - `appRoot: frontend` in buildspec — must match the env var
  - `buildPath: '/'` so install runs from monorepo root where `pnpm-lock.yaml` lives
  - `baseDirectory` is relative to `buildPath`, so `frontend/.next` (NOT `.next`)
  - `.npmrc` at repo root with `node-linker=hoisted` — pnpm's default isolated linker creates symlinks Amplify's SSR runtime can't follow ("`node_modules` folder is missing the 'next' dependency").
- **First-build webhook**: Amplify installs a GitHub webhook on the connected repo. The `AMPLIFY_GH_TOKEN` PAT must have `repo` + `admin:repo_hook`. If you see `BadRequestException: There was an issue setting up your repository` referencing `repos/webhooks`, the token's webhook scope is missing.

### CORS

- **`AllowOrigins`** must be **origins** (`scheme://host`), not full URLs. The `infra/envs/prod/main.tf` has both `local.redirect_urls` (with `/sign-in` for Cognito callbacks) and `local.allowed_origins` (no path for CORS) — don't conflate them.
- **Don't put a JWT authorizer on the `$default` route.** It runs on `OPTIONS` preflight (which has no `Authorization` header), returns 401, browser treats preflight as failed → "Failed to fetch" on every cross-origin write. The lambda already validates Cognito JWT in `backend/app/deps.py:current_principal` — that's the only auth gate needed.

### Lambda permissions (Function URL)

- **`function_url_auth_type` is only valid on `lambda:InvokeFunctionUrl`**, never on `lambda:InvokeFunction`. AWS now returns `InvalidParameterValueException: FunctionUrlAuthType is only supported for lambda:InvokeFunctionUrl action`. The webhook module keeps both permissions (URL needs the base invoke action too) but `aws_lambda_permission.url_invoke_function` must omit the field.

### Terragrunt + state bucket

- **`disable_bucket_update = true`** in `infra/envs/prod/terragrunt.hcl` — terragrunt otherwise prompts y/n to re-apply its default bucket policy (TLS enforcement, root-access block) and EOFs in CI.
- **`--terragrunt-non-interactive`** on `init`/`apply` — belt-and-braces for any other prompt.

### Cognito

- Hosted UI domain root (e.g. `https://mcp-platform-prod.auth.ap-southeast-2.amazoncognito.com/`) returns nothing useful. The login page is at `/login?response_type=code&client_id=...&redirect_uri=...&scope=...`.
- Default email sender is unreliable for Gmail (rate-limited, often filtered to spam). For dev / one-off password resets, use `aws cognito-idp admin-set-user-password ... --no-permanent` to set a known temp password directly; user changes it on first login.
- Callback URLs must be **full URLs** (`https://host/sign-in`), distinct from CORS origins.
- Adding the Amplify URL to Cognito callbacks would create a circular dep if read from `aws_amplify_app.default_domain`: `cognito_user_pool_client.callback_urls → amplify_app.default_domain` while `amplify_app.environment_variables → cognito_user_pool_client.id`. Hardcode the Amplify default-domain string in `deploy.yml`'s `FRONTEND_DOMAIN` env var instead.

### Frontend auth pattern

- `app/(app)/layout.tsx` wraps in `<AuthGate>` (client-side check, redirect to `/sign-in` if no Cognito tokens).
- `app/(auth)/sign-in/page.tsx` calls `configureAmplify()` on mount + listens to Amplify `Hub` for `signedIn` / `signInWithRedirect` events to redirect to `/dashboard` once tokens land. **Both halves are needed**: without `AuthGate`, the empty UI shell is publicly served; without the sign-in page handling the OAuth callback, users loop back to the login button after Cognito redirect.

### Backend errors / debuggability

- `frontend/lib/api.ts:request` throws `ApiError` whose message includes method + path + status + FastAPI `detail`. Network/CORS failures get status `0` and `Network error:` prefix. Toast UI surfaces these. When the human reports an error, ask them to copy-paste the toast.

## Useful one-liners

```bash
# Verify CORS preflight
curl -sSI -X OPTIONS "$API/secrets" \
  -H "Origin: https://main.d30245m5kpo4p6.amplifyapp.com" \
  -H "Access-Control-Request-Method: POST"

# Pull deployed terraform outputs (account-level admin creds required)
aws s3 cp s3://mcp-platform-tfstate-668532754740/prod/terraform.tfstate -

# Tail backend lambda logs
aws logs tail /aws/lambda/mcp-platform-prod-backend --follow

# Reset Cognito admin password to a known temp string
aws cognito-idp admin-set-user-password \
  --user-pool-id ap-southeast-2_jBwJtjPGl \
  --username <email> --password '<temp>' --no-permanent
```

## Avoid

- Mutating Amplify / Cognito / API Gateway via `aws ... update-*` outside terraform. OK for diagnosis (read), not for changes (write). Drift will haunt the next apply.
- Setting `iam_service_role_arn` on the Amplify app from terraform.
- Putting paths in CORS `AllowOrigins`.
- Putting JWT authorizers on `$default` routes.
- Skipping the `pr.yml` CI hooks.
