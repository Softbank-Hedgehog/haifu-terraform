variable "name_prefix" {
  description = "Name prefix for resources"
  type        = string
}

variable "cpu" {
  description = "CPU units for the task"
  type        = string
  default     = "256"
}

variable "memory" {
  description = "Memory for the task"
  type        = string
  default     = "512"
}

variable "container_name" {
  description = "Container name"
  type        = string
  default     = "app"
}

variable "container_image" {
  description = "Container image"
  type        = string
}

variable "container_port" {
  description = "Container port"
  type        = number
  default     = 80
}

variable "desired_count" {
  description = "Desired number of tasks"
  type        = number
  default     = 1
}

variable "subnet_ids" {
  description = "Subnet IDs"
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security group IDs"
  type        = list(string)
}

variable "assign_public_ip" {
  description = "Assign public IP"
  type        = bool
  default     = false
}

variable "target_group_arn" {
  description = "Target group ARN"
  type        = string
  default     = null
}

variable "execution_role_arn" {
  description = "Task execution role ARN"
  type        = string
}

variable "task_role_arn" {
  description = "Task role ARN"
  type        = string
  default     = null
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "environment_variables" {
  description = "Environment variables"
  type        = list(object({
    name  = string
    value = string
  }))
  default = []
}

variable "enable_autoscaling" {
  description = "Enable autoscaling"
  type        = bool
  default     = false
}

variable "min_capacity" {
  description = "Minimum capacity"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum capacity"
  type        = number
  default     = 10
}

variable "cpu_target_value" {
  description = "CPU target value for autoscaling"
  type        = number
  default     = 70
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}