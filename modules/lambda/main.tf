# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "${var.name_prefix}-lambda-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
  
  tags = var.tags
}

# Basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# VPC execution policy (if VPC is enabled)
resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  count      = length(var.subnet_ids) > 0 ? 1 : 0
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# S3 access policy
resource "aws_iam_role_policy_attachment" "lambda_s3" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}

# EventBridge access policy
resource "aws_iam_role_policy_attachment" "lambda_eventbridge" {
  count      = var.enable_eventbridge ? 1 : 0
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEventBridgeFullAccess"
}

# SQS access policy
resource "aws_iam_role_policy_attachment" "lambda_sqs" {
  count      = var.enable_sqs ? 1 : 0
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSQSFullAccess"
}

# DynamoDB access policy
resource "aws_iam_role_policy_attachment" "lambda_dynamodb" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
}

# API Gateway access policy
resource "aws_iam_role_policy_attachment" "lambda_apigw" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonAPIGatewayInvokeFullAccess"
}

# Lambda functions
resource "aws_lambda_function" "functions" {
  count = length(var.lambdas)
  
  function_name                  = "${var.name_prefix}-${var.lambdas[count.index].name}"
  filename                      = var.lambdas[count.index].filename
  handler                       = var.lambdas[count.index].handler
  runtime                       = var.lambdas[count.index].runtime
  role                          = aws_iam_role.lambda_role.arn
  timeout                       = var.lambdas[count.index].timeout
  memory_size                   = var.lambdas[count.index].memory_size
  reserved_concurrent_executions = var.lambdas[count.index].reserved_concurrent_executions > 0 ? var.lambdas[count.index].reserved_concurrent_executions : null
  
  dynamic "vpc_config" {
    for_each = var.lambdas[count.index].vpc_config && length(var.subnet_ids) > 0 ? [1] : []
    content {
      subnet_ids         = var.subnet_ids
      security_group_ids = var.security_group_ids
    }
  }
  
  tags = var.tags
}

# SQS Queue (if enabled)
resource "aws_sqs_queue" "main" {
  count = var.enable_sqs ? 1 : 0
  
  name = "${var.name_prefix}-lambda-queue"
  
  tags = var.tags
}

# SQS Dead Letter Queue
resource "aws_sqs_queue" "dlq" {
  count = var.enable_sqs ? 1 : 0
  
  name = "${var.name_prefix}-lambda-dlq"
  
  tags = var.tags
}

# EventBridge Rule (if enabled)
resource "aws_cloudwatch_event_rule" "deployment_event" {
  count = var.enable_eventbridge ? 1 : 0
  
  name        = "${var.name_prefix}-deployment-event"
  description = "Trigger Lambda on deployment events"
  
  event_pattern = jsonencode({
    source = ["aws.codepipeline", "aws.codebuild", "aws.codedeploy"]
    "detail-type" = [
      "CodePipeline Pipeline Execution State Change",
      "CodeBuild Build State Change",
      "CodeDeploy Deployment State-change Notification"
    ]
  })
  
  tags = var.tags
}

# EventBridge Target (if enabled and deployment lambda exists)
resource "aws_cloudwatch_event_target" "deployment_lambda" {
  count = var.enable_eventbridge && length([for l in var.lambdas : l if l.name == "deployment"]) > 0 ? 1 : 0
  
  rule      = aws_cloudwatch_event_rule.deployment_event[0].name
  target_id = "DeploymentLambda"
  arn       = aws_lambda_function.functions[index([for l in var.lambdas : l.name], "deployment")].arn
}

# Lambda permission for EventBridge
resource "aws_lambda_permission" "allow_eventbridge" {
  count = var.enable_eventbridge && length([for l in var.lambdas : l if l.name == "deployment"]) > 0 ? 1 : 0
  
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.functions[index([for l in var.lambdas : l.name], "deployment")].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.deployment_event[0].arn
}