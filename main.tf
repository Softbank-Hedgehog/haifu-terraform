# Get current AWS account ID
data "aws_caller_identity" "current" {}

module "vpc" {
  source = "./modules/vpc"
}

# ACM Certificate (using existing certificate)
# module "acm" {
#   source = "./modules/acm"
#   
#   domain_name = "haifu.cloud"
#   subject_alternative_names = ["*.haifu.cloud"]
#   
#   tags = local.common_tags
# }

module "alb" {
  source = "./modules/alb"
  
  name_prefix        = local.name_prefix
  vpc_id            = module.vpc.vpc_id
  subnet_ids        = module.vpc.public_subnets
  security_group_ids = [module.vpc.default_security_group_id]
  # certificate_arn   = "arn:aws:acm:us-east-1:895169747692:certificate/30cc6903-fe92-43a0-97af-8db8d6ded87b"
  
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
      custom_policy_names = ["secrets-manager-access", "ecr-access"]
    },
    {
      name                = "ecs-task-role"
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
      managed_policy_arns = []
      custom_policy_names = ["secrets-manager-access", "dynamodb-access-v2", "s3-access", "lambda-invoke-access"]
    },
    {
      name                = "codebuild-role"
      assume_role_policy  = jsonencode({
        Version = "2012-10-17"
        Statement = [
          {
            Action = "sts:AssumeRole"
            Effect = "Allow"
            Principal = {
              Service = "codebuild.amazonaws.com"
            }
          }
        ]
      })
      managed_policy_arns = ["arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"]
      custom_policy_names = []
    }
  ]
  
  custom_policies = [
    {
      name = "secrets-manager-access"
      policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
          {
            Effect = "Allow"
            Action = [
              "secretsmanager:GetSecretValue",
              "secretsmanager:DescribeSecret"
            ]
            Resource = "arn:aws:secretsmanager:ap-northeast-2:${data.aws_caller_identity.current.account_id}:secret:haifu-server-main*"
          }
        ]
      })
    },
    {
      name = "ecr-access"
      policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
          {
            Effect = "Allow"
            Action = [
              "ecr:GetAuthorizationToken",
              "ecr:BatchCheckLayerAvailability",
              "ecr:GetDownloadUrlForLayer",
              "ecr:BatchGetImage"
            ]
            Resource = "*"
          }
        ]
      })
    },
    {
      name = "dynamodb-access-v2"
      policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
          {
            Effect = "Allow"
            Action = [
              "dynamodb:*"
            ]
            Resource = [
              "arn:aws:dynamodb:ap-northeast-2:${data.aws_caller_identity.current.account_id}:table/*"
            ]
          }
        ]
      })
    },
    {
      name = "s3-access"
      policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
          {
            Effect = "Allow"
            Action = [
              "s3:PutObject"
            ]
            Resource = [
              "arn:aws:s3:::*/*"
            ]
          }
        ]
      })
    },
    {
      name = "lambda-invoke-access"
      policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
          {
            Effect = "Allow"
            Action = [
              "lambda:InvokeFunction"
            ]
            Resource = "*"
          }
        ]
      })
    }
  ]
  
  tags = local.common_tags
}

# Platform Backend ECS (FastAPI)
module "platform_backend" {
  source = "./modules/ecs-fargate"
  
  name_prefix           = local.name_prefix
  cluster_name          = "platform"
  service_name          = "backend"
  container_image       = "${aws_ecr_repository.backend.repository_url}:latest"
  container_port        = 8000
  cpu                   = "512"
  memory                = "1024"
  desired_count         = 2
  
  vpc_id                = module.vpc.vpc_id
  subnet_ids            = module.vpc.private_subnets
  security_group_ids    = [module.vpc.default_security_group_id]
  alb_target_group_arn  = module.alb.backend_target_group_arn
  execution_role_arn    = module.iam.role_arns["ecs-execution-role"]
  task_role_arn         = module.iam.role_arns["ecs-task-role"]
  
  enable_autoscaling    = true
  min_capacity          = 1
  max_capacity          = 5
  cpu_target_value      = 50
  
  environment_variables = [
    {
      name  = "ENV"
      value = var.environment
    },
    {
      name  = "AWS_REGION"
      value = var.aws_region
    }
  ]
  
  secrets = [
    {
      name      = "ENVIRONMENT"
      valueFrom = "arn:aws:secretsmanager:ap-northeast-2:${data.aws_caller_identity.current.account_id}:secret:haifu-server-main:ENVIRONMENT::"
    },
    {
      name      = "GITHUB_CLIENT_ID"
      valueFrom = "arn:aws:secretsmanager:ap-northeast-2:${data.aws_caller_identity.current.account_id}:secret:haifu-server-main:GITHUB_CLIENT_ID::"
    },
    {
      name      = "GITHUB_CLIENT_SECRET"
      valueFrom = "arn:aws:secretsmanager:ap-northeast-2:${data.aws_caller_identity.current.account_id}:secret:haifu-server-main:GITHUB_CLIENT_SECRET::"
    },
    {
      name      = "JWT_SECRET_KEY"
      valueFrom = "arn:aws:secretsmanager:ap-northeast-2:${data.aws_caller_identity.current.account_id}:secret:haifu-server-main:JWT_SECRET_KEY::"
    },
    {
      name      = "JWT_ALGORITHM"
      valueFrom = "arn:aws:secretsmanager:ap-northeast-2:${data.aws_caller_identity.current.account_id}:secret:haifu-server-main:JWT_ALGORITHM::"
    },
    {
      name      = "JWT_EXPIRE_DAYS"
      valueFrom = "arn:aws:secretsmanager:ap-northeast-2:${data.aws_caller_identity.current.account_id}:secret:haifu-server-main:JWT_EXPIRE_DAYS::"
    },
    {
      name      = "FRONTEND_URL"
      valueFrom = "arn:aws:secretsmanager:ap-northeast-2:${data.aws_caller_identity.current.account_id}:secret:haifu-server-main:FRONTEND_URL::"
    },
    {
      name      = "DYNAMODB_PROJECTS_TABLE"
      valueFrom = "arn:aws:secretsmanager:ap-northeast-2:${data.aws_caller_identity.current.account_id}:secret:haifu-server-main:DYNAMODB_PROJECTS_TABLE::"
    },
    {
      name      = "DYNAMODB_SERVICES_TABLE"
      valueFrom = "arn:aws:secretsmanager:ap-northeast-2:${data.aws_caller_identity.current.account_id}:secret:haifu-server-main:DYNAMODB_SERVICES_TABLE::"
    },
    {
      name      = "PORT"
      valueFrom = "arn:aws:secretsmanager:ap-northeast-2:${data.aws_caller_identity.current.account_id}:secret:haifu-server-main:PORT::"
    },
    {
      name      = "SOURCE_BUCKET_NAME"
      valueFrom = "arn:aws:secretsmanager:ap-northeast-2:${data.aws_caller_identity.current.account_id}:secret:haifu-server-main:SOURCE_BUCKET_NAME::"
    }
  ]
  
  tags = local.common_tags
}

# User Services ECS Cluster (for user deployments)
module "user_services" {
  source = "./modules/ecs-fargate"
  
  name_prefix           = local.name_prefix
  cluster_name          = "user-services"
  service_name          = "default-app"
  container_image       = "nginx:latest"
  container_port        = 80
  cpu                   = "256"
  memory                = "512"
  desired_count         = 1
  
  vpc_id                = module.vpc.vpc_id
  subnet_ids            = module.vpc.private_subnets
  security_group_ids    = [module.vpc.default_security_group_id]
  alb_target_group_arn  = module.alb.target_group_arn
  execution_role_arn    = module.iam.role_arns["ecs-execution-role"]
  task_role_arn         = module.iam.role_arns["ecs-task-role"]
  
  enable_autoscaling    = true
  min_capacity          = 1
  max_capacity          = 3
  cpu_target_value      = 70
  
  tags = local.common_tags
}

module "dynamodb" {
  source = "./modules/dynamodb"
  
  name_prefix = ""
  
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
    },
    {
      name         = "haifu-projects"
      hash_key     = "project_id"
      range_key    = ""
      billing_mode = "PAY_PER_REQUEST"
      attributes = [
        {
          name = "project_id"
          type = "S"
        },
        {
          name = "user_id"
          type = "S"
        }
      ]
      global_secondary_indexes = [
        {
          name            = "user-index"
          hash_key        = "user_id"
          range_key       = null
          projection_type = "ALL"
        }
      ]
    },
    {
      name         = "haifu-services"
      hash_key     = "service_id"
      range_key    = ""
      billing_mode = "PAY_PER_REQUEST"
      attributes = [
        {
          name = "service_id"
          type = "S"
        },
        {
          name = "project_id"
          type = "S"
        }
      ]
      global_secondary_indexes = [
        {
          name            = "project-index"
          hash_key        = "project_id"
          range_key       = null
          projection_type = "ALL"
        }
      ]
    },
    {
      name         = "snapshots"
      hash_key     = "snapshot_id"
      range_key    = ""
      billing_mode = "PAY_PER_REQUEST"
      attributes = [
        {
          name = "snapshot_id"
          type = "S"
        },
        {
          name = "service_id"
          type = "S"
        }
      ]
      global_secondary_indexes = [
        {
          name            = "service-index"
          hash_key        = "service_id"
          range_key       = null
          projection_type = "ALL"
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
      filename                      = "lambda-functions/deployment_lambda_debug.zip"
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

# API Gateway for Agent Lambda
resource "aws_api_gateway_rest_api" "agent_api" {
  name = "${local.name_prefix}-agent-api"
  
  tags = local.common_tags
}

resource "aws_api_gateway_resource" "agent_proxy" {
  rest_api_id = aws_api_gateway_rest_api.agent_api.id
  parent_id   = aws_api_gateway_rest_api.agent_api.root_resource_id
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_method" "agent_proxy" {
  rest_api_id   = aws_api_gateway_rest_api.agent_api.id
  resource_id   = aws_api_gateway_resource.agent_proxy.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "agent_lambda" {
  rest_api_id = aws_api_gateway_rest_api.agent_api.id
  resource_id = aws_api_gateway_method.agent_proxy.resource_id
  http_method = aws_api_gateway_method.agent_proxy.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = "arn:aws:apigateway:${var.aws_region}:lambda:path/2015-03-31/functions/${module.lambda.lambda_function_arns["agent"]}/invocations"
}

resource "aws_api_gateway_deployment" "agent_api" {
  depends_on = [
    aws_api_gateway_method.agent_proxy,
    aws_api_gateway_integration.agent_lambda,
  ]

  rest_api_id = aws_api_gateway_rest_api.agent_api.id
  stage_name  = "prod"
}

resource "aws_lambda_permission" "agent_api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda.lambda_function_names["agent"]
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.agent_api.execution_arn}/*/*"
}

# REST API Gateway for WebSocket Lambda
resource "aws_api_gateway_rest_api" "websocket_rest_api" {
  name = "${local.name_prefix}-websocket-rest-api"
  
  tags = local.common_tags
}

resource "aws_api_gateway_resource" "websocket_proxy" {
  rest_api_id = aws_api_gateway_rest_api.websocket_rest_api.id
  parent_id   = aws_api_gateway_rest_api.websocket_rest_api.root_resource_id
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_method" "websocket_proxy" {
  rest_api_id   = aws_api_gateway_rest_api.websocket_rest_api.id
  resource_id   = aws_api_gateway_resource.websocket_proxy.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "websocket_lambda" {
  rest_api_id = aws_api_gateway_rest_api.websocket_rest_api.id
  resource_id = aws_api_gateway_method.websocket_proxy.resource_id
  http_method = aws_api_gateway_method.websocket_proxy.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = "arn:aws:apigateway:${var.aws_region}:lambda:path/2015-03-31/functions/${module.lambda.lambda_function_arns["websocket"]}/invocations"
}

resource "aws_api_gateway_deployment" "websocket_rest_api" {
  depends_on = [
    aws_api_gateway_method.websocket_proxy,
    aws_api_gateway_integration.websocket_lambda,
  ]

  rest_api_id = aws_api_gateway_rest_api.websocket_rest_api.id
  stage_name  = "prod"
}

resource "aws_lambda_permission" "websocket_rest_api_gateway" {
  statement_id  = "AllowExecutionFromRestAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda.lambda_function_names["websocket"]
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.websocket_rest_api.execution_arn}/*/*"
}

# REST API Gateway for Deployment Lambda
resource "aws_api_gateway_rest_api" "deployment_api" {
  name = "${local.name_prefix}-deployment-api"
  
  tags = local.common_tags
}

resource "aws_api_gateway_resource" "deployment_proxy" {
  rest_api_id = aws_api_gateway_rest_api.deployment_api.id
  parent_id   = aws_api_gateway_rest_api.deployment_api.root_resource_id
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_method" "deployment_proxy" {
  rest_api_id   = aws_api_gateway_rest_api.deployment_api.id
  resource_id   = aws_api_gateway_resource.deployment_proxy.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "deployment_lambda" {
  rest_api_id = aws_api_gateway_rest_api.deployment_api.id
  resource_id = aws_api_gateway_method.deployment_proxy.resource_id
  http_method = aws_api_gateway_method.deployment_proxy.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = "arn:aws:apigateway:${var.aws_region}:lambda:path/2015-03-31/functions/${module.lambda.lambda_function_arns["deployment"]}/invocations"
}

resource "aws_api_gateway_deployment" "deployment_api" {
  depends_on = [
    aws_api_gateway_method.deployment_proxy,
    aws_api_gateway_integration.deployment_lambda,
  ]

  rest_api_id = aws_api_gateway_rest_api.deployment_api.id
  stage_name  = "prod"
}

resource "aws_lambda_permission" "deployment_api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda.lambda_function_names["deployment"]
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.deployment_api.execution_arn}/*/*"
}

# ECR Repository for backend
resource "aws_ecr_repository" "backend" {
  name = "${local.name_prefix}-backend"
  
  image_scanning_configuration {
    scan_on_push = true
  }
  
  tags = local.common_tags
}

# Backend Pipeline
module "backend_pipeline" {
  source = "./modules/backend-pipeline"
  
  name_prefix = "${local.name_prefix}-backend"
  
  github_owner  = "Softbank-Hedgehog"
  github_repo   = "haifu-server"
  github_branch = "main"
  
  ecr_repository_uri = aws_ecr_repository.backend.repository_url
  ecs_cluster_name   = module.platform_backend.cluster_name
  ecs_service_name   = module.platform_backend.service_name
  
  tags = local.common_tags
}

# Frontend S3 + CloudFront
module "frontend" {
  source = "./modules/s3-cloudfront"
  
  name_prefix     = "${local.name_prefix}-frontend"
  domain_name     = "haifu.cloud"
  certificate_arn = "arn:aws:acm:us-east-1:895169747692:certificate/30cc6903-fe92-43a0-97af-8db8d6ded87b"
  tags            = local.common_tags
}

# Frontend Pipeline
module "frontend_pipeline" {
  source = "./modules/frontend-pipeline"
  
  name_prefix = "${local.name_prefix}-frontend"
  
  github_owner  = "Softbank-Hedgehog"
  github_repo   = "haifu-client"
  github_branch = "main"
  
  s3_bucket_name             = module.frontend.bucket_name
  cloudfront_distribution_id = module.frontend.cloudfront_distribution_id
  backend_api_url           = "http://${module.alb.load_balancer_dns_name}/api"
  websocket_api_url         = module.websocket_api.websocket_stage_url
  
  tags = local.common_tags
}

