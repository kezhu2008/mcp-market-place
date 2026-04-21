variable "name" { type = string }
variable "admin_email" { type = string }
variable "redirect_urls" { type = list(string) }

resource "aws_cognito_user_pool" "pool" {
  name = var.name

  auto_verified_attributes = ["email"]
  username_attributes      = ["email"]

  password_policy {
    minimum_length    = 12
    require_lowercase = true
    require_uppercase = true
    require_numbers   = true
    require_symbols   = false
  }

  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  schema {
    name                = "email"
    attribute_data_type = "String"
    mutable             = true
    required            = true
  }
}

resource "aws_cognito_user_pool_domain" "domain" {
  domain       = var.name
  user_pool_id = aws_cognito_user_pool.pool.id
}

resource "aws_cognito_user_pool_client" "client" {
  name                                 = "${var.name}-web"
  user_pool_id                         = aws_cognito_user_pool.pool.id
  generate_secret                      = false
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  callback_urls                        = var.redirect_urls
  logout_urls                          = var.redirect_urls
  supported_identity_providers         = ["COGNITO"]
  explicit_auth_flows                  = ["ALLOW_REFRESH_TOKEN_AUTH", "ALLOW_USER_SRP_AUTH"]
}

resource "aws_cognito_user" "admin" {
  user_pool_id = aws_cognito_user_pool.pool.id
  username     = var.admin_email

  attributes = {
    email          = var.admin_email
    email_verified = "true"
  }
}

output "user_pool_id" { value = aws_cognito_user_pool.pool.id }
output "client_id" { value = aws_cognito_user_pool_client.client.id }
output "domain" { value = "${aws_cognito_user_pool_domain.domain.domain}.auth.${data.aws_region.current.name}.amazoncognito.com" }

data "aws_region" "current" {}
