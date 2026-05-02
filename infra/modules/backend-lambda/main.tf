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
  default = 60
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

# IAM role the platform-managed AgentCore harnesses assume. Required by
# CreateAgentRuntime; passed through iam:PassRole in the policy below.
# Empty default allowed for dev; the iam:PassRole statement falls back to a
# never-resolving placeholder ARN so the policy stays valid until the
# operator wires a real role.
variable "platform_harness_role_arn" {
  type    = string
  default = ""
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
  # Needed by POST /bots/{id}/test-function. Mirrors the webhook lambda's
  # permission. If the test endpoint is removed, drop this statement too.
  statement {
    actions   = ["bedrock-agentcore:InvokeAgentRuntime"]
    resources = ["arn:aws:bedrock-agentcore:*:*:runtime/*"]
  }
  # Needed by /gateways CRUD: the backend provisions AgentCore gateways
  # from an OpenAPI spec + token (CreateApiKeyCredentialProvider →
  # CreateGateway → CreateGatewayTarget) and tears them down on delete.
  # Note: the boto3 client name is `bedrock-agentcore-control`, but the
  # IAM action prefix is `bedrock-agentcore` for both control and data
  # plane operations.
  statement {
    actions = [
      "bedrock-agentcore:CreateGateway",
      "bedrock-agentcore:CreateGatewayTarget",
      "bedrock-agentcore:CreateApiKeyCredentialProvider",
      "bedrock-agentcore:DeleteGateway",
      "bedrock-agentcore:DeleteGatewayTarget",
      "bedrock-agentcore:DeleteApiKeyCredentialProvider",
      "bedrock-agentcore:GetGateway",
      "bedrock-agentcore:ListGateways",
    ]
    resources = ["*"]
  }
  # Needed by /harnesses CRUD: the backend provisions AgentCore runtimes
  # (CreateAgentRuntime) and tears them down on delete.
  statement {
    actions = [
      "bedrock-agentcore:CreateAgentRuntime",
      "bedrock-agentcore:UpdateAgentRuntime",
      "bedrock-agentcore:DeleteAgentRuntime",
      "bedrock-agentcore:GetAgentRuntime",
      "bedrock-agentcore:ListAgentRuntimes",
    ]
    resources = ["*"]
  }
  # CreateAgentRuntime attaches the platform harness role to the new runtime;
  # passing the role requires explicit iam:PassRole. Falls back to a
  # placeholder ARN so the policy validates when the operator hasn't wired
  # a real role yet (CreateAgentRuntime will then fail with a clear AWS
  # error rather than a terraform-validate one).
  statement {
    actions = ["iam:PassRole"]
    resources = [
      var.platform_harness_role_arn != "" ? var.platform_harness_role_arn : "arn:aws:iam::000000000000:role/platform-harness-unconfigured",
    ]
  }
  # Gateway data-plane invocation for POST /gateways/{id}/test
  # (SigV4-signed tools/list against the gateway URL).
  statement {
    actions   = ["bedrock-agentcore:InvokeMCPTool"]
    resources = ["arn:aws:bedrock-agentcore:*:*:gateway/*"]
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
