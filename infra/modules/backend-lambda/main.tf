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
  # AgentCore control plane + data plane. The IAM surface for AgentCore is
  # still firming up — CreateAgentRuntime implicitly requires
  # CreateAgentRuntimeEndpoint, there are sibling actions for versions /
  # endpoints / credential providers, plus data-plane Invoke* (Runtime,
  # MCPTool). Rather than enumerate every action and chase
  # AccessDeniedException through deploys, grant the whole namespace on
  # `*`. Tighten once the action list is stable.
  statement {
    actions   = ["bedrock-agentcore:*"]
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
