remote_state {
  backend = "s3"
  generate = {
    path      = "backend.tf"
    if_exists = "overwrite_terragrunt"
  }
  config = {
    # Populate these from bootstrap outputs.
    bucket         = get_env("TF_STATE_BUCKET", "mcp-platform-tfstate-CHANGE_ME")
    key            = "prod/terraform.tfstate"
    region         = "ap-southeast-2"
    dynamodb_table = get_env("TF_LOCK_TABLE", "mcp-platform-tflock")
    encrypt        = true
  }
}

generate "provider" {
  path      = "provider.tf"
  if_exists = "overwrite_terragrunt"
  contents  = <<EOF
terraform {
  required_version = ">= 1.7.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.70" }
  }
}

provider "aws" {
  region = "ap-southeast-2"
}
EOF
}

inputs = {
  project           = "mcp-platform"
  env               = "prod"
  region            = "ap-southeast-2"
  admin_email       = get_env("ADMIN_EMAIL", "admin@example.com")
  github_repo       = "kezhu2008/mcp-market-place"
  amplify_token     = get_env("AMPLIFY_GH_TOKEN", "")
  frontend_domain   = get_env("FRONTEND_DOMAIN", "")
  default_tenant_id = "t_default"
}
