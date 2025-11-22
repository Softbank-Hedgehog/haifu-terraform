output "load_balancer_arn" {
  description = "Load balancer ARN"
  value       = aws_lb.main.arn
}

output "load_balancer_dns_name" {
  description = "Load balancer DNS name"
  value       = aws_lb.main.dns_name
}

output "load_balancer_zone_id" {
  description = "Load balancer zone ID"
  value       = aws_lb.main.zone_id
}

output "target_group_arn" {
  description = "Target group ARN"
  value       = aws_lb_target_group.main.arn
}

output "backend_target_group_arn" {
  description = "Backend target group ARN"
  value       = aws_lb_target_group.backend.arn
}

output "listener_arn" {
  description = "ALB listener ARN"
  value       = var.certificate_arn != null ? aws_lb_listener.https[0].arn : aws_lb_listener.http.arn
}

output "security_group_id" {
  description = "ALB security group ID"
  value       = var.security_group_ids[0]
}