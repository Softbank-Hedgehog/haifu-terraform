variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-2"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "haifu"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}