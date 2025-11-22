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

output "alb_http_endpoint" {
  description = "ALB HTTP endpoint"
  value       = "http://${module.alb.load_balancer_dns_name}"
}

output "alb_https_endpoint" {
  description = "ALB HTTPS endpoint (if certificate configured)"
  value       = "https://${module.alb.load_balancer_dns_name}"
}

output "platform_cluster_id" {
  description = "Platform ECS cluster ID"
  value       = module.platform_backend.cluster_id
}

output "user_services_cluster_id" {
  description = "User services ECS cluster ID"
  value       = module.user_services.cluster_id
}

output "platform_service_name" {
  description = "Platform backend service name"
  value       = module.platform_backend.service_name
}

output "user_services_cluster_name" {
  description = "User services cluster name"
  value       = module.user_services.cluster_name
}

output "dynamodb_table_names" {
  description = "DynamoDB table names"
  value       = module.dynamodb.table_names
}

output "websocket_api_endpoint" {
  description = "WebSocket API endpoint"
  value       = module.websocket_api.websocket_stage_url
}

output "agent_http_api_endpoint" {
  description = "Agent HTTP API endpoint"
  value       = module.agent_http_api.invoke_url
}

output "agent_api_routes" {
  description = "Agent API available routes"
  value = {
    main       = "${module.agent_http_api.invoke_url}/main"
    chat       = "${module.agent_http_api.invoke_url}/chat"
    deployment = "${module.agent_http_api.invoke_url}/deployment"
    cost       = "${module.agent_http_api.invoke_url}/cost"
  }
}

output "lambda_function_names" {
  description = "Lambda function names"
  value       = module.lambda.lambda_function_names
}

output "ecr_repository_url" {
  description = "ECR repository URL for backend"
  value       = aws_ecr_repository.backend.repository_url
}

output "frontend_website_url" {
  description = "Frontend website URL"
  value       = module.frontend.website_url
}

output "frontend_s3_bucket" {
  description = "Frontend S3 bucket name"
  value       = module.frontend.bucket_name
}

output "frontend_cloudfront_distribution_id" {
  description = "Frontend CloudFront distribution ID"
  value       = module.frontend.cloudfront_distribution_id
}

