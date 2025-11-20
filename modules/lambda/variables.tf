variable "name_prefix" {
  description = "Name prefix for resources"
  type        = string
}

variable "function_name" {
  description = "Lambda function name"
  type        = string
}

variable "filename" {
  description = "Path to the function's deployment package"
  type        = string
}

variable "handler" {
  description = "Function entrypoint"
  type        = string
  default     = "index.handler"
}

variable "runtime" {
  description = "Runtime environment"
  type        = string
  default     = "python3.9"
}

variable "timeout" {
  description = "Function timeout"
  type        = number
  default     = 30
}

variable "memory_size" {
  description = "Memory size"
  type        = number
  default     = 128
}

variable "source_code_hash" {
  description = "Source code hash"
  type        = string
  default     = null
}

variable "environment_variables" {
  description = "Environment variables"
  type        = map(string)
  default     = {}
}

variable "subnet_ids" {
  description = "Subnet IDs for VPC configuration"
  type        = list(string)
  default     = null
}

variable "security_group_ids" {
  description = "Security group IDs for VPC configuration"
  type        = list(string)
  default     = null
}

variable "custom_policy" {
  description = "Custom IAM policy"
  type        = string
  default     = null
}

variable "sqs_queue_arn" {
  description = "SQS queue ARN for event source"
  type        = string
  default     = null
}

variable "sqs_batch_size" {
  description = "SQS batch size"
  type        = number
  default     = 10
}

variable "schedule_expression" {
  description = "Schedule expression for CloudWatch Events"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}