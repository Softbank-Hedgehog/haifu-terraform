variable "user_id" {
  description = "User ID for resource naming"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
}

variable "github_repo_url" {
  description = "GitHub repository URL"
  type        = string
}

variable "github_branch" {
  description = "GitHub branch to deploy"
  type        = string
  default     = "main"
}

variable "build_command" {
  description = "Build command (AI generated)"
  type        = string
  default     = "npm run build"
}

variable "build_output_dir" {
  description = "Build output directory"
  type        = string
  default     = "dist"
}

variable "node_version" {
  description = "Node.js version"
  type        = string
  default     = "20"
}

variable "environment_variables" {
  description = "Environment variables for build"
  type        = map(string)
  default     = {}
}

variable "custom_domain" {
  description = "Custom domain for the site"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}