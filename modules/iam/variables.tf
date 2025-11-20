variable "name_prefix" {
  description = "Name prefix for resources"
  type        = string
}

variable "roles" {
  description = "IAM roles to create"
  type = list(object({
    name                  = string
    assume_role_policy    = string
    managed_policy_arns   = list(string)
    custom_policy_names   = list(string)
  }))
  default = []
}

variable "custom_policies" {
  description = "Custom IAM policies to create"
  type = list(object({
    name   = string
    policy = string
  }))
  default = []
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}