resource "aws_sqs_queue" "main" {
  name                      = "${var.name_prefix}-${var.queue_name}"
  delay_seconds             = var.delay_seconds
  max_message_size          = var.max_message_size
  message_retention_seconds = var.message_retention_seconds
  receive_wait_time_seconds = var.receive_wait_time_seconds
  visibility_timeout_seconds = var.visibility_timeout_seconds

  dynamic "redrive_policy" {
    for_each = var.enable_dlq ? [1] : []
    content {
      deadLetterTargetArn = aws_sqs_queue.dlq[0].arn
      maxReceiveCount     = var.max_receive_count
    }
  }

  tags = var.tags
}

resource "aws_sqs_queue" "dlq" {
  count = var.enable_dlq ? 1 : 0
  name  = "${var.name_prefix}-${var.queue_name}-dlq"

  tags = var.tags
}

resource "aws_sqs_queue_policy" "main" {
  count     = var.queue_policy != null ? 1 : 0
  queue_url = aws_sqs_queue.main.id
  policy    = var.queue_policy
}