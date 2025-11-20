resource "aws_lambda_event_source_mapping" "sqs" {
  count            = var.sqs_queue_arn != null ? 1 : 0
  event_source_arn = var.sqs_queue_arn
  function_name    = aws_lambda_function.main.arn
  batch_size       = var.sqs_batch_size
}

resource "aws_cloudwatch_event_rule" "schedule" {
  count               = var.schedule_expression != null ? 1 : 0
  name                = "${var.name_prefix}-schedule"
  description         = "Schedule for ${var.function_name}"
  schedule_expression = var.schedule_expression

  tags = var.tags
}

resource "aws_cloudwatch_event_target" "lambda" {
  count     = var.schedule_expression != null ? 1 : 0
  rule      = aws_cloudwatch_event_rule.schedule[0].name
  target_id = "LambdaTarget"
  arn       = aws_lambda_function.main.arn
}

resource "aws_lambda_permission" "allow_cloudwatch" {
  count         = var.schedule_expression != null ? 1 : 0
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.main.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.schedule[0].arn
}