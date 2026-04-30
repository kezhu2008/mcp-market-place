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
