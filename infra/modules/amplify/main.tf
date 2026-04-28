variable "name" {
  type = string
}

variable "repository" {
  type = string
}

variable "branch" {
  type    = string
  default = "main"
}

variable "access_token" {
  type      = string
  sensitive = true
}

variable "env" {
  type = map(string)
}

resource "aws_amplify_app" "app" {
  name                        = var.name
  repository                  = "https://github.com/${var.repository}"
  access_token                = var.access_token
  platform                    = "WEB_COMPUTE"
  enable_branch_auto_build    = true
  enable_auto_branch_creation = false

  environment_variables = var.env

  build_spec = <<YAML
version: 1
applications:
  - appRoot: frontend
    frontend:
      phases:
        preBuild:
          commands:
            - corepack enable
            - pnpm install --frozen-lockfile
        build:
          commands:
            - pnpm build
      artifacts:
        baseDirectory: .next
        files:
          - '**/*'
      cache:
        paths:
          - node_modules/**/*
YAML

  # iam_service_role_arn intentionally unset on this apply — let terraform
  # detach the previously-broken role so Amplify auto-creates a fresh one
  # on the next build. After that build succeeds, lifecycle.ignore_changes
  # will be re-added so terraform doesn't clobber the auto-created role.
}

resource "aws_amplify_branch" "branch" {
  app_id      = aws_amplify_app.app.id
  branch_name = var.branch
  stage       = "PRODUCTION"
  framework   = "Next.js - SSR"
}

output "app_id" {
  value = aws_amplify_app.app.id
}

output "default_domain" {
  value = "${aws_amplify_branch.branch.branch_name}.${aws_amplify_app.app.default_domain}"
}
