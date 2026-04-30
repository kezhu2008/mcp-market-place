variable "name" {
  type = string
}

variable "source_zip" {
  type = string
}

variable "handler" {
  type    = string
  default = "handler.handler"
}

variable "runtime" {
  type    = string
  default = "python3.12"
}

variable "timeout" {
  type    = number
  default = 60
}

variable "memory" {
  type    = number
  default = 256
}

variable "table_arn" {
  type = string
}

variable "secrets_prefix_arn" {
  type = string
}

variable "env" {
  type = map(string)
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
    actions   = ["dynamodb:Query", "dynamodb:PutItem", "dynamodb:GetItem"]
    resources = [var.table_arn, "${var.table_arn}/index/*"]
  }
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [var.secrets_prefix_arn]
  }
  # AgentCore harness invocation. Resource pattern uses wildcards because
  # bot-configured ARNs may live in any region/account the operator has
  # granted via the harness's resource policy.
  statement {
    actions   = ["bedrock-agentcore:InvokeAgentRuntime"]
    resources = ["arn:aws:bedrock-agentcore:*:*:runtime/*"]
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

resource "aws_lambda_function_url" "url" {
  function_name      = aws_lambda_function.fn.function_name
  authorization_type = "NONE"
}

# Function URL with AuthType=NONE requires explicit resource-based policy
# entries granting lambda:InvokeFunctionUrl (and lambda:InvokeFunction, per the
# AWS console banner) to principal "*"; without them the URL returns 403
# Forbidden to unsigned callers (e.g. Telegram).
resource "aws_lambda_permission" "url_invoke" {
  statement_id           = "AllowPublicInvokeFunctionUrl"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.fn.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_lambda_permission" "url_invoke_function" {
  statement_id           = "AllowPublicInvokeFunction"
  action                 = "lambda:InvokeFunction"
  function_name          = aws_lambda_function.fn.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

output "function_name" {
  value = aws_lambda_function.fn.function_name
}

output "function_arn" {
  value = aws_lambda_function.fn.arn
}

output "url" {
  value = aws_lambda_function_url.url.function_url
}
