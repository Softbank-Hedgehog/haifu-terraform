variable "name_prefix" {
  description = "Name prefix for resources"
  type        = string
}

variable "lambda_function_arn" {
  description = "Lambda function ARN for WebSocket handler"
  type        = string
}

variable "lambda_function_name" {
  description = "Lambda function name for WebSocket handler"
  type        = string
}

variable "routes" {
  description = "WebSocket routes configuration"
  type = list(object({
    route_key = string
  }))
  default = [
    { route_key = "deploy_status" },
    { route_key = "$connect" },
    { route_key = "$disconnect" }
  ]
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}