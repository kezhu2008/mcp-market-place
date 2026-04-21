# Bootstrap (one-time, manual)

Run once per AWS account before any CI/CD can work. Creates:

- S3 bucket for Terraform remote state (versioned, encrypted)
- DynamoDB table for state locks
- GitHub OIDC identity provider
- IAM role `github-actions-deploy` trusting the `kezhu2008/mcp-market-place` repo

After this, the main workflow in `.github/workflows/deploy.yml` takes over — no manual AWS console work is needed for subsequent deploys.

## Prereqs

- AWS CLI configured (SSO profile or access key) with admin-ish rights in the target account.
- Terraform ≥ 1.7.

## Steps

```bash
cd infra/bootstrap

# 1. Copy the example tfvars and fill in your account id.
cp example.tfvars terraform.tfvars
$EDITOR terraform.tfvars

# 2. Init (local backend — NOT S3; this module creates the bucket).
terraform init -backend=false

# 3. Plan + apply.
terraform plan  -var-file=terraform.tfvars -out=plan
terraform apply plan
```

## Outputs to copy into `infra/envs/prod/terragrunt.hcl`

- `state_bucket` → `remote_state.config.bucket`
- `lock_table`   → `remote_state.config.dynamodb_table`
- `deploy_role_arn` → paste into GitHub secrets as `AWS_DEPLOY_ROLE_ARN`

## GitHub OIDC trust

The created role trusts tokens with:
- `repo:kezhu2008/mcp-market-place:ref:refs/heads/main`
- `repo:kezhu2008/mcp-market-place:pull_request`

Adjust via `var.github_repo` if your fork differs.
