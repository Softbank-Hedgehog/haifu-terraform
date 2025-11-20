variable "name_prefix" {
  description = "Name prefix for resources"
  type        = string
}

variable "bucket_suffix" {
  description = "Bucket suffix"
  type        = string
  default     = "static"
}

variable "default_root_object" {
  description = "Default root object"
  type        = string
  default     = "index.html"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}