output "websocket_api_id" {
  description = "WebSocket API ID"
  value       = aws_apigatewayv2_api.websocket_api.id
}

output "websocket_api_endpoint" {
  description = "WebSocket API endpoint"
  value       = aws_apigatewayv2_api.websocket_api.api_endpoint
}

output "websocket_stage_url" {
  description = "WebSocket stage URL"
  value       = "wss://${aws_apigatewayv2_api.websocket_api.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${aws_apigatewayv2_stage.websocket_stage.name}"
}

data "aws_region" "current" {}