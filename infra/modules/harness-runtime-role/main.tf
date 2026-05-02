// IAM role assumed by AgentCore harness runtimes (the container created by
// CreateAgentRuntime). The platform-default container image needs:
//   - Foundation model access for the model the user picked (via the
//     MODEL_ID env var)
//   - bedrock-agentcore:InvokeMCPTool on gateway/* so the harness can call
//     the gateways the user linked
//   - CloudWatch Logs for stdout/stderr
//
// Operators can override this by setting `var.platform_harness_role_arn` on
// the env to a role they manage themselves; in that case this module's
// output is unused (the env-level main.tf wires the override through to
// backend_lambda).

variable "name" { type = string }

data "aws_iam_policy_document" "trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["bedrock-agentcore.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "role" {
  name               = var.name
  assume_role_policy = data.aws_iam_policy_document.trust.json
}

data "aws_iam_policy_document" "perms" {
  // Foundation model access. Scoping to a specific model is brittle when
  // the platform exposes a dropdown of allowed models; use the foundation-
  // model arn pattern. Tighten if your account has a smaller allowlist.
  statement {
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
    ]
    resources = ["arn:aws:bedrock:*::foundation-model/*"]
  }
  // Call platform gateways as MCP tools. Same wildcards as the backend
  // lambda's grant — the runtime acts on behalf of the harness's tenant.
  statement {
    actions   = ["bedrock-agentcore:InvokeMCPTool"]
    resources = ["arn:aws:bedrock-agentcore:*:*:gateway/*"]
  }
  // ECR image pull. AgentCore validates these are present on the
  // execution role at CreateAgentRuntime time, even though the ECR repo
  // also grants the AgentCore service principal — both are required.
  // GetAuthorizationToken doesn't support resource-level scoping.
  statement {
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }
  statement {
    actions = [
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
      "ecr:DescribeImages",
    ]
    resources = ["arn:aws:ecr:*:*:repository/*"]
  }
  statement {
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["arn:aws:logs:*:*:*"]
  }
}

resource "aws_iam_role_policy" "perms" {
  role   = aws_iam_role.role.id
  policy = data.aws_iam_policy_document.perms.json
}

output "role_arn" {
  value = aws_iam_role.role.arn
}
