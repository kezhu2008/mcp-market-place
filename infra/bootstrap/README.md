# Bootstrap (one-time, manual)

Run once per AWS account before any CI/CD can work. Creates the Terraform state bucket + lock table. After this, `infra/envs/prod` owns everything else.

## Prereqs

- AWS CLI configured with admin-ish rights.
- Terraform ≥ 1.7.

## Step 1 — create the state backend

```bash
cd infra/bootstrap
cp example.tfvars terraform.tfvars
$EDITOR terraform.tfvars                  # usually no edits needed

terraform init -backend=false
terraform apply
```

Outputs:
- `state_bucket`  → paste into GitHub secret `TF_STATE_BUCKET`
- `lock_table`    → paste into GitHub secret `TF_LOCK_TABLE`

## Step 2 — create a deploy IAM user + access key

Create an IAM user `mcp-platform-deploy` with programmatic access and the policy below attached inline (or as a managed policy). Save the access key id + secret somewhere safe — you'll paste them into GitHub secrets next.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "TFStateAccess",
      "Effect": "Allow",
      "Action": ["s3:GetObject","s3:PutObject","s3:DeleteObject","s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::mcp-platform-tfstate-<ACCOUNT_ID>",
        "arn:aws:s3:::mcp-platform-tfstate-<ACCOUNT_ID>/*"
      ]
    },
    {
      "Sid": "TFLockAccess",
      "Effect": "Allow",
      "Action": ["dynamodb:*"],
      "Resource": "arn:aws:dynamodb:ap-southeast-2:<ACCOUNT_ID>:table/mcp-platform-tflock"
    },
    {
      "Sid": "ProjectWrite",
      "Effect": "Allow",
      "Action": [
        "iam:*","lambda:*","apigateway:*","dynamodb:*","cognito-idp:*",
        "secretsmanager:*","s3:*","amplify:*","logs:*","cloudwatch:*",
        "cloudformation:*","sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

Tighten `ProjectWrite` to specific resource prefixes once you've applied once and know the exact ARNs.

## Step 3 — set GitHub secrets

In `Settings → Secrets and variables → Actions`, add:

| Secret | Value |
|---|---|
| `AWS_ACCESS_KEY_ID`  | from Step 2 |
| `AWS_SECRET_ACCESS_KEY` | from Step 2 |
| `TF_STATE_BUCKET` | Step 1 output |
| `TF_LOCK_TABLE` | Step 1 output |
| `ADMIN_EMAIL` | the email to seed into Cognito as the sole admin |
| `AMPLIFY_GH_TOKEN` | GitHub PAT with `repo` scope, used by Amplify to clone + webhook |

Merging to `main` now runs `deploy.yml` which applies `infra/envs/prod`.

## Rotation

Rotate the deploy user's access key quarterly. The only GitHub-side change is updating two secrets — no infra edits.
