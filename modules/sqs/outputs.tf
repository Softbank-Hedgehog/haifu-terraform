output "queue_id" {
  description = "SQS queue ID"
  value       = aws_sqs_queue.main.id
}

output "queue_arn" {
  description = "SQS queue ARN"
  value       = aws_sqs_queue.main.arn
}

output "queue_url" {
  description = "SQS queue URL"
  value       = aws_sqs_queue.main.url
}

output "dlq_id" {
  description = "Dead letter queue ID"
  value       = var.enable_dlq ? aws_sqs_queue.dlq[0].id : null
}

output "dlq_arn" {
  description = "Dead letter queue ARN"
  value       = var.enable_dlq ? aws_sqs_queue.dlq[0].arn : null
}