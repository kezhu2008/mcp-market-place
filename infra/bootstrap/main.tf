terraform {
  required_version = ">= 1.7.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.70" }
  }
}

provider "aws" {
  region = var.region
}

variable "region" {
  type    = string
  default = "ap-southeast-2"
}

variable "aws_account_id" {
  type = string
}

variable "project" {
  type    = string
  default = "mcp-platform"
}

variable "github_repo" {
  type    = string
  default = "kezhu2008/mcp-market-place"
}

locals {
  state_bucket = "${var.project}-tfstate-${var.aws_account_id}"
  lock_table   = "${var.project}-tflock"
  role_name    = "github-actions-deploy"
}

# ── Terraform state backend ──────────────────────────────────────────
resource "aws_s3_bucket" "state" {
  bucket        = local.state_bucket
  force_destroy = false
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "lock" {
  name         = local.lock_table
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"
  attribute {
    name = "LockID"
    type = "S"
  }
}

# ── GitHub OIDC trust ────────────────────────────────────────────────
resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd"
  ]
}

data "aws_iam_policy_document" "deploy_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:${var.github_repo}:ref:refs/heads/main",
        "repo:${var.github_repo}:pull_request",
      ]
    }
  }
}

resource "aws_iam_role" "deploy" {
  name               = local.role_name
  assume_role_policy = data.aws_iam_policy_document.deploy_trust.json
}

# Broad but scoped to this project's resources. Tighten later.
data "aws_iam_policy_document" "deploy_perms" {
  statement {
    sid    = "TFState"
    effect = "Allow"
    actions = [
      "s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.state.arn,
      "${aws_s3_bucket.state.arn}/*",
    ]
  }
  statement {
    sid       = "TFLock"
    effect    = "Allow"
    actions   = ["dynamodb:*"]
    resources = [aws_dynamodb_table.lock.arn]
  }
  statement {
    sid    = "ProjectWrite"
    effect = "Allow"
    actions = [
      "iam:*",
      "lambda:*",
      "apigateway:*",
      "dynamodb:*",
      "cognito-idp:*",
      "secretsmanager:*",
      "s3:*",
      "amplify:*",
      "logs:*",
      "cloudwatch:*",
      "cloudformation:*",
      "sts:GetCallerIdentity",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "deploy" {
  role   = aws_iam_role.deploy.id
  policy = data.aws_iam_policy_document.deploy_perms.json
}

output "state_bucket" { value = aws_s3_bucket.state.id }
output "lock_table"   { value = aws_dynamodb_table.lock.name }
output "deploy_role_arn" { value = aws_iam_role.deploy.arn }
