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

resource "aws_iam_role" "amplify" {
  name = "${var.name}-amplify-service"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "amplify.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "amplify" {
  role       = aws_iam_role.amplify.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AdministratorAccess-Amplify"
}

resource "aws_amplify_app" "app" {
  name                        = var.name
  repository                  = "https://github.com/${var.repository}"
  access_token                = var.access_token
  iam_service_role_arn        = aws_iam_role.amplify.arn
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
        baseDirectory: frontend/.next
        files:
          - '**/*'
      cache:
        paths:
          - frontend/node_modules/**/*
YAML
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
