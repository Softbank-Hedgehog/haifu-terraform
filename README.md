# Haifu Terraform

AWS infrastructure as code using Terraform.

## Structure

- `bootstrap/` - S3 & DynamoDB for remote state (run once)
- `modules/` - Reusable Terraform modules
  - `vpc/` - VPC with subnets and security groups
  - `alb/` - Application Load Balancer
  - `ecs-fargate/` - ECS Fargate cluster and services
  - `lambda/` - Lambda functions with SQS and EventBridge
  - `iam/` - IAM roles and policies
  - `s3-cloudfront/` - S3 bucket with CloudFront
- `env/` - Environment-specific configurations
- `lambda-functions/` - Lambda function code and packages

## Usage

### 1. Bootstrap (First time only)
```bash
cd bootstrap
terraform init
terraform apply
cd ..
```

### 2. Deploy Infrastructure
```bash
# Development
terraform init
terraform plan -var-file="env/dev.tfvars"
terraform apply -var-file="env/dev.tfvars"

# Production
terraform plan -var-file="env/prod.tfvars"
terraform apply -var-file="env/prod.tfvars"
```

## Resources Created

- **VPC**: 10.0.0.0/16 with public/private subnets
- **ALB**: Application Load Balancer for web traffic
- **ECS**: Fargate cluster running nginx
- **Lambda**: Agent and Deployment functions
- **SQS**: Message queues with DLQ
- **EventBridge**: Event-driven architecture
- **S3**: Static website hosting with CloudFront