output "lambda_function_arns" {
  description = "ARNs of Lambda functions"
  value       = { for i, lambda in var.lambdas : lambda.name => aws_lambda_function.functions[i].arn }
}

output "lambda_function_names" {
  description = "Names of Lambda functions"
  value       = { for i, lambda in var.lambdas : lambda.name => aws_lambda_function.functions[i].function_name }
}

output "iam_role_arn" {
  description = "IAM role ARN for Lambda functions"
  value       = aws_iam_role.lambda_role.arn
}

output "sqs_queue_url" {
  description = "SQS queue URL"
  value       = var.enable_sqs ? aws_sqs_queue.main[0].url : null
}

output "sqs_dlq_url" {
  description = "SQS DLQ URL"
  value       = var.enable_sqs ? aws_sqs_queue.dlq[0].url : null
}