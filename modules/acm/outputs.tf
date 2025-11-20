output "certificate_arn" {
  description = "ACM certificate ARN"
  value       = aws_acm_certificate.main.arn
}

output "certificate_domain_validation_options" {
  description = "Certificate domain validation options"
  value       = aws_acm_certificate.main.domain_validation_options
}

output "certificate_status" {
  description = "Certificate status"
  value       = aws_acm_certificate.main.status
}