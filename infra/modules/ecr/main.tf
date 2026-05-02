# Private ECR repository for platform-built container images.
#
# Used to store the AgentCore harness image. The repository policy grants
# pull access to the `bedrock-agentcore.amazonaws.com` service principal so
# AgentCore Runtime can fetch the image when CreateAgentRuntime runs.

variable "name" {
  type = string
}

# Number of tagged images to retain. Older images expire automatically.
variable "image_retention_count" {
  type    = number
  default = 10
}

resource "aws_ecr_repository" "repo" {
  name                 = var.name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "policy" {
  repository = aws_ecr_repository.repo.name
  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep the last ${var.image_retention_count} images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = var.image_retention_count
        }
        action = { type = "expire" }
      },
    ]
  })
}

# Allow Bedrock AgentCore service to pull the image when CreateAgentRuntime
# spins up the container. Without this, the runtime fails with
# `Public ECR resource not found` (or its private-ECR equivalent) because
# the AgentCore service principal isn't authorized.
data "aws_iam_policy_document" "pull" {
  statement {
    sid    = "AllowAgentCorePull"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["bedrock-agentcore.amazonaws.com"]
    }
    actions = [
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
      "ecr:DescribeImages",
    ]
  }
}

resource "aws_ecr_repository_policy" "pull" {
  repository = aws_ecr_repository.repo.name
  policy     = data.aws_iam_policy_document.pull.json
}

output "repository_url" {
  value = aws_ecr_repository.repo.repository_url
}

output "repository_arn" {
  value = aws_ecr_repository.repo.arn
}

output "repository_name" {
  value = aws_ecr_repository.repo.name
}
