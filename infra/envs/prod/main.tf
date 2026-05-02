variable "project" {
  type = string
}

variable "env" {
  type = string
}

variable "region" {
  type = string
}

variable "admin_email" {
  type = string
}

variable "github_repo" {
  type = string
}

variable "amplify_token" {
  type      = string
  sensitive = true
  default   = ""
}

variable "frontend_domain" {
  type    = string
  default = ""
}

variable "default_tenant_id" {
  type    = string
  default = "t_default"
}

# IAM role assumed by platform-managed AgentCore harness runtimes. Empty
# string (the default) means "let the platform create one" — see
# module.harness_runtime_role below. Set to a custom role ARN to override.
variable "platform_harness_role_arn" {
  type    = string
  default = ""
}

# Override the platform-built harness image URI. Empty (default) means
# "use the image we build + push to module.harness_ecr below". Set to a
# specific URI to pin to an external image (e.g. a vendor-supplied one).
variable "platform_harness_image_uri" {
  type    = string
  default = ""
}

# Tag of the platform-built harness image. CI passes the commit SHA; the
# default makes a fresh `terragrunt apply` from a workstation pull
# whatever image happens to be tagged `latest`.
variable "platform_harness_image_tag" {
  type    = string
  default = "latest"
}

data "aws_caller_identity" "current" {}

locals {
  account_id     = data.aws_caller_identity.current.account_id
  prefix         = "${var.project}-${var.env}"
  table_name     = "${var.project}_${var.env}"
  secrets_prefix = var.project
  secrets_arn    = "arn:aws:secretsmanager:${var.region}:${local.account_id}:secret:${local.secrets_prefix}/*"
  redirect_urls = var.frontend_domain != "" ? [
    "https://${var.frontend_domain}/sign-in",
    "http://localhost:3000/sign-in",
  ] : ["http://localhost:3000/sign-in"]
  # CORS expects origins (scheme://host), not full URLs with paths.
  allowed_origins = var.frontend_domain != "" ? [
    "https://${var.frontend_domain}",
    "http://localhost:3000",
  ] : ["http://localhost:3000"]
}

module "dynamodb" {
  source = "../../modules/dynamodb"
  name   = local.table_name
}

module "cognito" {
  source        = "../../modules/cognito"
  name          = local.prefix
  admin_email   = var.admin_email
  redirect_urls = local.redirect_urls
}

module "harness_runtime_role" {
  source = "../../modules/harness-runtime-role"
  name   = "${local.prefix}-harness-runtime"
}

module "harness_ecr" {
  source = "../../modules/ecr"
  name   = "${local.prefix}-harness"
}

locals {
  # Effective role ARN passed to the backend lambda: operator override
  # wins, otherwise the platform-managed role from the module above.
  effective_harness_role_arn = (
    var.platform_harness_role_arn != ""
    ? var.platform_harness_role_arn
    : module.harness_runtime_role.role_arn
  )

  # Effective harness image URI: operator override wins, otherwise the
  # platform-built image at the configured tag in our private ECR.
  effective_harness_image_uri = (
    var.platform_harness_image_uri != ""
    ? var.platform_harness_image_uri
    : "${module.harness_ecr.repository_url}:${var.platform_harness_image_tag}"
  )
}

module "webhook_lambda" {
  source             = "../../modules/webhook-lambda"
  name               = "${local.prefix}-webhook"
  source_zip         = "${path.module}/../../../webhook/build/function.zip"
  table_arn          = module.dynamodb.arn
  secrets_prefix_arn = local.secrets_arn
  env = {
    TABLE_NAME     = module.dynamodb.name
    SECRETS_PREFIX = local.secrets_prefix
  }
}

module "backend_lambda" {
  source                    = "../../modules/backend-lambda"
  name                      = "${local.prefix}-backend"
  source_zip                = "${path.module}/../../../backend/build/function.zip"
  table_arn                 = module.dynamodb.arn
  secrets_prefix_arn        = local.secrets_arn
  platform_harness_role_arn = local.effective_harness_role_arn
  env = {
    TABLE_NAME                 = module.dynamodb.name
    SECRETS_PREFIX             = local.secrets_prefix
    COGNITO_USER_POOL_ID       = module.cognito.user_pool_id
    COGNITO_CLIENT_ID          = module.cognito.client_id
    WEBHOOK_BASE_URL           = module.webhook_lambda.url
    DEFAULT_TENANT_ID          = var.default_tenant_id
    PLATFORM_HARNESS_ROLE_ARN  = local.effective_harness_role_arn
    PLATFORM_HARNESS_IMAGE_URI = local.effective_harness_image_uri
  }
}

module "api" {
  source               = "../../modules/api-gateway"
  name                 = "${local.prefix}-api"
  lambda_arn           = module.backend_lambda.function_arn
  lambda_name          = module.backend_lambda.function_name
  cognito_user_pool_id = module.cognito.user_pool_id
  cognito_client_id    = module.cognito.client_id
  region               = var.region
  allow_origins        = local.allowed_origins
}

module "amplify" {
  count        = var.amplify_token != "" ? 1 : 0
  source       = "../../modules/amplify"
  name         = local.prefix
  repository   = var.github_repo
  access_token = var.amplify_token
  env = {
    # Monorepo: tells Amplify the Next.js app lives at <repo-root>/frontend.
    # Without this, Amplify reads the root package.json and errors with
    # "Cannot read 'next' version in package.json".
    AMPLIFY_MONOREPO_APP_ROOT        = "frontend"
    NEXT_PUBLIC_API_BASE_URL         = module.api.api_url
    NEXT_PUBLIC_COGNITO_USER_POOL_ID = module.cognito.user_pool_id
    NEXT_PUBLIC_COGNITO_CLIENT_ID    = module.cognito.client_id
    NEXT_PUBLIC_COGNITO_DOMAIN       = module.cognito.domain
    NEXT_PUBLIC_COGNITO_REDIRECT_URI = length(local.redirect_urls) > 0 ? local.redirect_urls[0] : ""
  }
}

output "api_url" {
  value = module.api.api_url
}

output "webhook_url" {
  value = module.webhook_lambda.url
}

output "cognito_user_pool_id" {
  value = module.cognito.user_pool_id
}

output "cognito_client_id" {
  value = module.cognito.client_id
}

output "cognito_domain" {
  value = module.cognito.domain
}

output "table_name" {
  value = module.dynamodb.name
}

output "harness_ecr_repository_url" {
  value = module.harness_ecr.repository_url
}

output "harness_ecr_repository_name" {
  value = module.harness_ecr.repository_name
}
