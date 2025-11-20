variable "name_prefix" {
  description = "Name prefix for resources"
  type        = string
}

variable "queue_name" {
  description = "SQS queue name"
  type        = string
}

variable "delay_seconds" {
  description = "Delay seconds"
  type        = number
  default     = 0
}

variable "max_message_size" {
  description = "Maximum message size"
  type        = number
  default     = 262144
}

variable "message_retention_seconds" {
  description = "Message retention seconds"
  type        = number
  default     = 345600
}

variable "receive_wait_time_seconds" {
  description = "Receive wait time seconds"
  type        = number
  default     = 0
}

variable "visibility_timeout_seconds" {
  description = "Visibility timeout seconds"
  type        = number
  default     = 30
}

variable "enable_dlq" {
  description = "Enable dead letter queue"
  type        = bool
  default     = false
}

variable "max_receive_count" {
  description = "Maximum receive count for DLQ"
  type        = number
  default     = 3
}

variable "queue_policy" {
  description = "SQS queue policy"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}