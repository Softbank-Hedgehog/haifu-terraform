variable "name_prefix" {
  description = "Name prefix for resources"
  type        = string
}

variable "lambdas" {
  description = "Lambda functions configuration"
  type = list(object({
    name                           = string
    filename                      = string
    handler                       = string
    runtime                       = string
    timeout                       = number
    memory_size                   = number
    reserved_concurrent_executions = number
    vpc_config                    = bool
  }))
  default = []
}

variable "subnet_ids" {
  description = "Subnet IDs for VPC configuration"
  type        = list(string)
  default     = []
}

variable "security_group_ids" {
  description = "Security group IDs for VPC configuration"
  type        = list(string)
  default     = []
}

variable "enable_sqs" {
  description = "Enable SQS integration"
  type        = bool
  default     = false
}

variable "enable_eventbridge" {
  description = "Enable EventBridge integration"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}