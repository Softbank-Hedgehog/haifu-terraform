module "vpc" {
  source = "./modules/vpc"
}

module "alb" {
  source = "./modules/alb"
  
  name_prefix        = local.name_prefix
  vpc_id            = module.vpc.vpc_id
  subnet_ids        = module.vpc.public_subnets
  security_group_ids = [module.vpc.default_security_group_id]
  
  tags = local.common_tags
}

module "iam" {
  source = "./modules/iam"
  
  name_prefix = local.name_prefix
  
  roles = [
    {
      name                = "ecs-execution-role"
      assume_role_policy  = jsonencode({
        Version = "2012-10-17"
        Statement = [
          {
            Action = "sts:AssumeRole"
            Effect = "Allow"
            Principal = {
              Service = "ecs-tasks.amazonaws.com"
            }
          }
        ]
      })
      managed_policy_arns = ["arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"]
      custom_policy_names = []
    }
  ]
  
  tags = local.common_tags
}

module "ecs" {
  source = "./modules/ecs-fargate"
  
  name_prefix        = local.name_prefix
  container_image    = "nginx:latest"
  subnet_ids         = module.vpc.private_subnets
  security_group_ids = [module.vpc.default_security_group_id]
  execution_role_arn = module.iam.role_arns["ecs-execution-role"]
  aws_region         = var.aws_region
  
  tags = local.common_tags
}

module "dynamodb" {
  source = "./modules/dynamodb"
  
  name_prefix = local.name_prefix
  
  tables = [
    {
      name         = "deployment-status"
      hash_key     = "deployment_id"
      range_key    = ""
      billing_mode = "PAY_PER_REQUEST"
      attributes = [
        {
          name = "deployment_id"
          type = "S"
        }
      ]
    }
  ]
  
  tags = local.common_tags
}

module "lambda" {
  source = "./modules/lambda"
  
  name_prefix = local.name_prefix
  
  lambdas = [
    {
      name                           = "agent"
      filename                      = "lambda-functions/agent_lambda.zip"
      handler                       = "agent_lambda.handler"
      runtime                       = "python3.11"
      timeout                       = 60
      memory_size                   = 512
      reserved_concurrent_executions = 0
      vpc_config                    = false
    },
    {
      name                           = "deployment"
      filename                      = "lambda-functions/deployment_lambda.zip"
      handler                       = "deployment_lambda.handler"
      runtime                       = "python3.11"
      timeout                       = 900
      memory_size                   = 1024
      reserved_concurrent_executions = 0
      vpc_config                    = false
    },
    {
      name                           = "websocket"
      filename                      = "lambda-functions/websocket_lambda.zip"
      handler                       = "websocket_lambda.handler"
      runtime                       = "python3.11"
      timeout                       = 60
      memory_size                   = 512
      reserved_concurrent_executions = 0
      vpc_config                    = false
    }
  ]
  
  enable_sqs        = true
  enable_eventbridge = true
  
  tags = local.common_tags
}

module "websocket_api" {
  source = "./modules/api-gateway-websocket"
  
  name_prefix           = local.name_prefix
  lambda_function_arn   = module.lambda.lambda_function_arns["websocket"]
  lambda_function_name  = module.lambda.lambda_function_names["websocket"]
  
  tags = local.common_tags
}

# module "s3" {
#   source = "./modules/s3-cloudfront"
#   
#   name_prefix = local.name_prefix
#   tags        = local.common_tags
# }

