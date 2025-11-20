variable "name_prefix" {
  description = "Name prefix for resources"
  type        = string
}

variable "artifact_bucket" {
  description = "S3 bucket for artifacts"
  type        = string
}

variable "source_bucket" {
  description = "S3 bucket for source code"
  type        = string
}

variable "source_object_key" {
  description = "S3 object key for source code"
  type        = string
}

variable "compute_type" {
  description = "CodeBuild compute type"
  type        = string
  default     = "BUILD_GENERAL1_SMALL"
}

variable "build_image" {
  description = "CodeBuild image"
  type        = string
  default     = "aws/codebuild/amazonlinux2-x86_64-standard:3.0"
}

variable "buildspec_file" {
  description = "Buildspec file path"
  type        = string
  default     = null
}

variable "environment_variables" {
  description = "Environment variables for CodeBuild"
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}