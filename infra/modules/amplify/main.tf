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

  # Amplify auto-creates a service role on first build. Don't let terraform
  # clobber it on subsequent applies. Per AWS docs:
  # https://docs.aws.amazon.com/amplify/latest/userguide/server-side-rendering-amplify.html
  lifecycle {
    ignore_changes = [iam_service_role_arn]
  }
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
