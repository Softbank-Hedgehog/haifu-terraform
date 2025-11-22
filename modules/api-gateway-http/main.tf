# HTTP API Gateway for Agent Lambda
resource "aws_apigatewayv2_api" "http_api" {
  name          = "${var.name_prefix}-agent-api"
  protocol_type = "HTTP"
  
  cors_configuration {
    allow_origins     = var.cors_allow_origins
    allow_methods     = ["GET", "POST", "OPTIONS"]
    allow_headers     = ["content-type", "authorization", "x-api-key"]
    allow_credentials = false
    max_age          = 300
  }
  
  tags = var.tags
}

# Lambda Integration
resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id           = aws_apigatewayv2_api.http_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = var.lambda_function_arn
  
  payload_format_version = "2.0"
  timeout_milliseconds   = var.timeout_milliseconds
}

# Routes
resource "aws_apigatewayv2_route" "routes" {
  count = length(var.routes)
  
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = var.routes[count.index].route_key
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# Stage (auto-deploy enabled)
resource "aws_apigatewayv2_stage" "default_stage" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true
  
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_logs.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
      errorMessage   = "$context.error.message"
    })
  }
  
  tags = var.tags
}

# CloudWatch Log Group for API Gateway logs
resource "aws_cloudwatch_log_group" "api_logs" {
  name              = "/aws/apigateway/${var.name_prefix}-agent-api"
  retention_in_days = var.log_retention_days
  
  tags = var.tags
}

# Lambda Permission
resource "aws_lambda_permission" "allow_apigw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}

