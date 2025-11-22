variable "name_prefix" {
  description = "Name prefix for resources"
  type        = string
}

variable "lambda_function_arn" {
  description = "Lambda function ARN for HTTP API handler"
  type        = string
}

variable "lambda_function_name" {
  description = "Lambda function name for HTTP API handler"
  type        = string
}

variable "routes" {
  description = "HTTP API routes configuration"
  type = list(object({
    route_key = string
  }))
  default = [
    { route_key = "POST /main" },
    { route_key = "POST /chat" },
    { route_key = "POST /deployment" },
    { route_key = "POST /cost" }
  ]
}

variable "cors_allow_origins" {
  description = "CORS allowed origins"
  type        = list(string)
  default     = ["*"]
}

variable "timeout_milliseconds" {
  description = "Lambda integration timeout in milliseconds"
  type        = number
  default     = 30000
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

