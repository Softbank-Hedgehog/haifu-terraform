# WebSocket API
resource "aws_apigatewayv2_api" "websocket_api" {
  name                      = "${var.name_prefix}-websocket"
  protocol_type             = "WEBSOCKET"
  route_selection_expression = "$request.body.action"
  
  tags = var.tags
}

# Lambda Integration
resource "aws_apigatewayv2_integration" "websocket_lambda" {
  api_id           = aws_apigatewayv2_api.websocket_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = var.lambda_function_arn
}

# Routes
resource "aws_apigatewayv2_route" "routes" {
  count = length(var.routes)
  
  api_id    = aws_apigatewayv2_api.websocket_api.id
  route_key = var.routes[count.index].route_key
  target    = "integrations/${aws_apigatewayv2_integration.websocket_lambda.id}"
}

# Deployment
resource "aws_apigatewayv2_deployment" "websocket_deployment" {
  api_id = aws_apigatewayv2_api.websocket_api.id
  
  depends_on = [aws_apigatewayv2_route.routes]
}

# Stage
resource "aws_apigatewayv2_stage" "websocket_stage" {
  api_id        = aws_apigatewayv2_api.websocket_api.id
  deployment_id = aws_apigatewayv2_deployment.websocket_deployment.id
  name          = "prod"
  
  tags = var.tags
}

# Lambda Permission
resource "aws_lambda_permission" "allow_apigw_websocket" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.websocket_api.execution_arn}/*/*"
}