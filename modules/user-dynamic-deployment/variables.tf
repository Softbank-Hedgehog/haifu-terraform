variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "service_name" {
  description = "Name of the user service"
  type        = string
}

variable "runtime" {
  description = "Runtime environment (nodejs18, python3.11, etc.)"
  type        = string
}

variable "cpu" {
  description = "CPU units for the task"
  type        = number
  default     = 256
}

variable "memory" {
  description = "Memory for the task"
  type        = number
  default     = 512
}

variable "container_port" {
  description = "Port the container listens on"
  type        = number
  default     = 80
}

variable "desired_count" {
  description = "Desired number of tasks"
  type        = number
  default     = 1
}

variable "min_capacity" {
  description = "Minimum number of tasks for auto-scaling"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum number of tasks for auto-scaling"
  type        = number
  default     = 10
}

variable "health_check_path" {
  description = "Health check path"
  type        = string
  default     = "/"
}

variable "listener_priority" {
  description = "ALB listener rule priority"
  type        = number
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs"
  type        = list(string)
}

variable "ecs_cluster_id" {
  description = "ECS cluster ID"
  type        = string
}

variable "ecs_cluster_name" {
  description = "ECS cluster name"
  type        = string
}

variable "execution_role_arn" {
  description = "ECS execution role ARN"
  type        = string
}

variable "task_role_arn" {
  description = "ECS task role ARN"
  type        = string
}

variable "alb_listener_arn" {
  description = "ALB listener ARN"
  type        = string
}

variable "alb_security_group_id" {
  description = "ALB security group ID"
  type        = string
}

variable "environment_variables" {
  description = "Environment variables for the container"
  type = list(object({
    name  = string
    value = string
  }))
  default = []
}

variable "build_environment_variables" {
  description = "Environment variables for CodeBuild"
  type        = map(string)
  default     = {}
}

variable "install_commands" {
  description = "Install commands for build"
  type        = list(string)
  default     = []
}

variable "build_commands" {
  description = "Build commands"
  type        = list(string)
  default     = []
}

variable "start_command" {
  description = "Start command for the service"
  type        = string
  default     = ""
}

variable "github_repository" {
  description = "GitHub repository (owner/repo)"
  type        = string
  default     = ""
}

variable "github_branch" {
  description = "GitHub branch"
  type        = string
  default     = "main"
}

variable "github_connection_arn" {
  description = "GitHub CodeStar connection ARN"
  type        = string
  default     = ""
}

variable "artifacts_bucket_name" {
  description = "S3 bucket for pipeline artifacts"
  type        = string
  default     = ""
}

variable "codepipeline_role_arn" {
  description = "CodePipeline service role ARN"
  type        = string
  default     = ""
}

variable "codebuild_role_arn" {
  description = "CodeBuild service role ARN"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}