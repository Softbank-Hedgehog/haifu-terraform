variable "name_prefix" {
  description = "Name prefix for resources"
  type        = string
}

variable "github_owner" {
  description = "GitHub repository owner"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
}

variable "github_branch" {
  description = "GitHub branch"
  type        = string
  default     = "main"
}

variable "s3_bucket_name" {
  description = "S3 bucket name for deployment"
  type        = string
}

variable "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  type        = string
}

variable "backend_api_url" {
  description = "Backend API URL for environment variables"
  type        = string
}

variable "websocket_api_url" {
  description = "WebSocket API URL for environment variables"
  type        = string
}



variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}