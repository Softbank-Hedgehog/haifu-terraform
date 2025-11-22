output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = aws_ecr_repository.user_service.repository_url
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.user_service.name
}

output "ecs_service_arn" {
  description = "ECS service ARN"
  value       = aws_ecs_service.user_service.id
}

output "target_group_arn" {
  description = "ALB target group ARN"
  value       = aws_lb_target_group.user_service.arn
}

output "security_group_id" {
  description = "Security group ID"
  value       = aws_security_group.user_service.id
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.user_service.name
}

output "service_endpoint" {
  description = "Service endpoint path"
  value       = "/${var.service_name}"
}