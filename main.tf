# Get current AWS account ID
data "aws_caller_identity" "current" {}

module "vpc" {
  source = "./modules/vpc"
}

# CloudFront용 ACM 인증서 (us-east-1)
data "aws_acm_certificate" "cloudfront" {
  provider = aws.us-east-1
  domain   = "haifu.cloud"
  statuses = ["ISSUED"]
}

module "alb" {
  source = "./modules/alb"
  
  name_prefix        = local.name_prefix
  vpc_id            = module.vpc.vpc_id
  subnet_ids        = module.vpc.public_subnets
  security_group_ids = [module.vpc.default_security_group_id]
  # certificate_arn   = module.acm.certificate_arn  # Uncomment when using ACM
  
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
      custom_policy_names = ["secrets-manager-access", "dynamodb-access-v2"]
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
  desired_count         = 0  # No default service running
  
  vpc_id                = module.vpc.vpc_id
  subnet_ids            = module.vpc.private_subnets
  security_group_ids    = [module.vpc.default_security_group_id]
  alb_target_group_arn  = module.alb.target_group_arn
  execution_role_arn    = module.iam.role_arns["ecs-execution-role"]
  task_role_arn         = module.iam.role_arns["ecs-task-role"]
  
  enable_autoscaling    = false
  
  tags = local.common_tags
}

# User deployments will be created dynamically by deployment Lambda
# Static deployments: S3 + CloudFront via CloudFormation
# Dynamic deployments: ECS Fargate services created on-demand

module "dynamodb" {
  source = "./modules/dynamodb"
  
  name_prefix = null
  
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
          name     = "user-index"
          hash_key = "user_id"
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
          name     = "project-index"
          hash_key = "project_id"
          projection_type = "ALL"
        }
      ]
    },
    {
      name         = "users"
      hash_key     = "user_id"
      range_key    = ""
      billing_mode = "PAY_PER_REQUEST"
      attributes = [
        {
          name = "user_id"
          type = "S"
        },
        {
          name = "github_id"
          type = "S"
        }
      ]
      global_secondary_indexes = [
        {
          name     = "github-index"
          hash_key = "github_id"
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

# Agent HTTP API
module "agent_http_api" {
  source = "./modules/api-gateway-http"
  
  name_prefix           = local.name_prefix
  lambda_function_arn   = module.lambda.lambda_function_arns["agent"]
  lambda_function_name  = module.lambda.lambda_function_names["agent"]
  
  routes = [
    { route_key = "POST /main" },
    { route_key = "POST /chat" },
    { route_key = "POST /deployment" },
    { route_key = "POST /cost" }
  ]
  
  cors_allow_origins = ["*"]  # 프로덕션에서는 특정 도메인으로 제한
  
  tags = local.common_tags
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
  certificate_arn = data.aws_acm_certificate.cloudfront.arn
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

