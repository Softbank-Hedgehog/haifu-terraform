output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.vpc.public_subnets
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = module.vpc.private_subnets
}

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = module.alb.load_balancer_dns_name
}

output "ecs_cluster_id" {
  description = "ECS cluster ID"
  value       = module.ecs.cluster_id
}

output "dynamodb_table_names" {
  description = "DynamoDB table names"
  value       = module.dynamodb.table_names
}

output "websocket_api_endpoint" {
  description = "WebSocket API endpoint"
  value       = module.websocket_api.websocket_stage_url
}

output "lambda_function_names" {
  description = "Lambda function names"
  value       = module.lambda.lambda_function_names
}

