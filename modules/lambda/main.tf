resource "aws_lambda_function" "main" {
  filename         = var.filename
  function_name    = "${var.name_prefix}-${var.function_name}"
  role            = aws_iam_role.lambda_role.arn
  handler         = var.handler
  source_code_hash = var.source_code_hash
  runtime         = var.runtime
  timeout         = var.timeout
  memory_size     = var.memory_size

  dynamic "environment" {
    for_each = length(var.environment_variables) > 0 ? [1] : []
    content {
      variables = var.environment_variables
    }
  }

  dynamic "vpc_config" {
    for_each = var.subnet_ids != null ? [1] : []
    content {
      subnet_ids         = var.subnet_ids
      security_group_ids = var.security_group_ids
    }
  }

  tags = var.tags
}