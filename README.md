# MCP Platform

A self-service control plane for wiring up Bots, Tools, MCP Servers, and Models.

Phase 1 scope: sign in, manage Telegram bot Secrets, create bots with slash-command → response pairs, deploy, and receive events — end-to-end on AWS with full CI/CD.

## Layout

```
frontend/   Next.js 15 (App Router) + TypeScript + Tailwind + shadcn/ui
backend/    FastAPI on Lambda (Python 3.12, Mangum adapter)
webhook/    Telegram webhook Lambda (isolated hot path)
infra/      Terraform + Terragrunt (modules + prod env)
.github/    CI/CD workflows (OIDC to AWS, no long-lived keys)
```

## Region

`ap-southeast-2` (Sydney).

## Getting started

1. One-time infra bootstrap — see `infra/bootstrap/README.md`.
2. Local dev of each package — see its own README.
3. After bootstrap, push to `main` triggers full deploy via GitHub Actions.

See `/root/.claude/plans/mcp-platform-phase-async-dream.md` for the full Phase 1 plan.
