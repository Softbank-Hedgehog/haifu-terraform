output "api_id" {
  description = "HTTP API Gateway ID"
  value       = aws_apigatewayv2_api.http_api.id
}

output "api_endpoint" {
  description = "HTTP API Gateway endpoint"
  value       = aws_apigatewayv2_api.http_api.api_endpoint
}

output "api_url" {
  description = "HTTP API Gateway URL (with stage)"
  value       = "${aws_apigatewayv2_api.http_api.api_endpoint}/${aws_apigatewayv2_stage.default_stage.name}"
}

output "stage_name" {
  description = "API Gateway stage name"
  value       = aws_apigatewayv2_stage.default_stage.name
}

output "invoke_url" {
  description = "Full invoke URL for the API"
  value       = aws_apigatewayv2_stage.default_stage.invoke_url
}

data "aws_region" "current" {}

