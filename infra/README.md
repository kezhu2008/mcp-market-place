# Infra

Terraform + Terragrunt, region `ap-southeast-2`.

```
infra/
├── bootstrap/          one-time: state bucket, lock table, GitHub OIDC role
├── modules/            reusable modules
│   ├── dynamodb/       single-table with GSI1 + GSI2
│   ├── cognito/        user pool + admin user + hosted UI client
│   ├── backend-lambda/ FastAPI Lambda + IAM
│   ├── webhook-lambda/ webhook Lambda + Function URL + IAM (read-only SM)
│   ├── api-gateway/    HTTP API + JWT authorizer → backend Lambda
│   └── amplify/        frontend hosting
└── envs/prod/          the one Phase-1 environment — composes all modules
```

## First-time setup

1. Run `infra/bootstrap` once (see its README).
2. Build the Lambda zips:
   ```bash
   ./scripts/build-backend.sh    # produces backend/build/function.zip
   ./scripts/build-webhook.sh    # produces webhook/build/function.zip
   ```
3. Apply prod:
   ```bash
   cd infra/envs/prod
   export TF_STATE_BUCKET=mcp-platform-tfstate-<acct>
   export TF_LOCK_TABLE=mcp-platform-tflock
   export AWS_ACCOUNT_ID=<acct>
   export ADMIN_EMAIL=you@example.com
   export AMPLIFY_GH_TOKEN=<gh-pat-with-repo-scope>
   terragrunt init
   terragrunt apply
   ```

## Destroying

```bash
cd infra/envs/prod && terragrunt destroy
# bootstrap resources must be destroyed manually; they hold state.
```

## Notes

- The backend Lambda reads `WEBHOOK_BASE_URL` from the webhook Lambda's Function URL — ordering is enforced by module dependency, no circular dep.
- `amplify` module is conditional on `AMPLIFY_GH_TOKEN`; without it, the frontend can be deployed from the GitHub Actions `deploy` workflow via `aws amplify start-deployment`.
