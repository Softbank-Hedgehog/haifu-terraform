variable "name_prefix" {
  description = "Name prefix for resources"
  type        = string
}

variable "tables" {
  description = "DynamoDB tables configuration"
  type = list(object({
    name         = string
    hash_key     = string
    range_key    = string
    attributes   = list(object({
      name = string
      type = string
    }))
    billing_mode = string
  }))
  default = []
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}