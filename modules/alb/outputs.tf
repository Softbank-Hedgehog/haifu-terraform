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