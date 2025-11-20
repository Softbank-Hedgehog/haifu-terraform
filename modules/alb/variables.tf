variable "name_prefix" {
  description = "Name prefix for resources"
  type        = string
}

variable "internal" {
  description = "Whether the load balancer is internal"
  type        = bool
  default     = false
}

variable "security_group_ids" {
  description = "Security group IDs"
  type        = list(string)
}

variable "subnet_ids" {
  description = "Subnet IDs"
  type        = list(string)
}

variable "enable_deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = false
}

variable "listener_port" {
  description = "Listener port"
  type        = string
  default     = "80"
}

variable "listener_protocol" {
  description = "Listener protocol"
  type        = string
  default     = "HTTP"
}

variable "target_port" {
  description = "Target port"
  type        = number
  default     = 80
}

variable "target_protocol" {
  description = "Target protocol"
  type        = string
  default     = "HTTP"
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "health_check_path" {
  description = "Health check path"
  type        = string
  default     = "/"
}

variable "certificate_arn" {
  description = "SSL certificate ARN"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}