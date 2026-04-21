variable "name" {
  type = string
}

variable "source_zip" {
  type = string
}

variable "handler" {
  type    = string
  default = "app.main.handler"
}

variable "runtime" {
  type    = string
  default = "python3.12"
}

variable "timeout" {
  type    = number
  default = 15
}

variable "memory" {
  type    = number
  default = 512
}

variable "env" {
  type = map(string)
}

variable "table_arn" {
  type = string
}

variable "secrets_prefix_arn" {
  type = string
}

data "aws_iam_policy_document" "trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "role" {
  name               = "${var.name}-role"
  assume_role_policy = data.aws_iam_policy_document.trust.json
}

resource "aws_iam_role_policy_attachment" "logs" {
  role       = aws_iam_role.role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "perms" {
  statement {
    actions   = ["dynamodb:*"]
    resources = [var.table_arn, "${var.table_arn}/index/*"]
  }
  statement {
    actions = [
      "secretsmanager:CreateSecret",
      "secretsmanager:PutSecretValue",
      "secretsmanager:GetSecretValue",
      "secretsmanager:DeleteSecret",
      "secretsmanager:DescribeSecret",
      "secretsmanager:UpdateSecret",
    ]
    resources = [var.secrets_prefix_arn]
  }
}

resource "aws_iam_role_policy" "perms" {
  role   = aws_iam_role.role.id
  policy = data.aws_iam_policy_document.perms.json
}

resource "aws_lambda_function" "fn" {
  function_name    = var.name
  role             = aws_iam_role.role.arn
  handler          = var.handler
  runtime          = var.runtime
  timeout          = var.timeout
  memory_size      = var.memory
  filename         = var.source_zip
  source_code_hash = filebase64sha256(var.source_zip)

  environment {
    variables = var.env
  }
}

output "function_name" {
  value = aws_lambda_function.fn.function_name
}

output "function_arn" {
  value = aws_lambda_function.fn.arn
}

output "role_arn" {
  value = aws_iam_role.role.arn
}
