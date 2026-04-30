variable "name" {
  type = string
}

variable "lambda_arn" {
  type = string
}

variable "lambda_name" {
  type = string
}

variable "cognito_user_pool_id" {
  type = string
}

variable "cognito_client_id" {
  type = string
}

variable "region" {
  type = string
}

variable "allow_origins" {
  type = list(string)
}

resource "aws_apigatewayv2_api" "api" {
  name          = var.name
  protocol_type = "HTTP"
  cors_configuration {
    allow_origins = var.allow_origins
    allow_methods = ["GET", "POST", "PATCH", "DELETE", "OPTIONS"]
    allow_headers = ["authorization", "content-type"]
    max_age       = 300
  }
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = var.lambda_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "health" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# All routes pass through unauthenticated at the API Gateway layer; the lambda
# enforces Cognito JWT validation itself (app/deps.py:current_principal).
# A JWT authorizer here breaks CORS preflight: $default also matches OPTIONS,
# the authorizer runs without an Authorization header, returns 401, browser
# treats the preflight as failed.
resource "aws_apigatewayv2_route" "any" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}

output "api_url" {
  value = aws_apigatewayv2_stage.default.invoke_url
}
