module "vpc" {
  source = "./modules/vpc"
}

module "alb" {
  source = "./modules/alb"
  
  name_prefix        = local.name_prefix
  vpc_id            = module.vpc.vpc_id
  subnet_ids        = module.vpc.public_subnets
  security_group_ids = []
  
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
  security_group_ids = []
  execution_role_arn = module.iam.role_arns["ecs-execution-role"]
  aws_region         = var.aws_region
  
  tags = local.common_tags
}

module "lambda" {
  source = "./modules/lambda"
  
  name_prefix   = local.name_prefix
  function_name = "${local.name_prefix}-example"
  filename      = "lambda_function.zip"
  handler       = "index.handler"
  runtime       = "python3.9"
  
  tags = local.common_tags
}

module "s3" {
  source = "./modules/s3-cloudfront"
  
  name_prefix = local.name_prefix
  tags        = local.common_tags
}

