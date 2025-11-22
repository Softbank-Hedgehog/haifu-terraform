variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-2"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "haifu"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "github_owner" {
  description = "GitHub repository owner"
  type        = string
  default     = ""
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
  default     = ""
}

variable "github_branch" {
  description = "GitHub branch"
  type        = string
  default     = "main"
}

variable "user_static_services" {
  description = "Map of user static services to deploy"
  type = map(object({
    github_owner     = string
    github_repo      = string
    github_branch    = string
    install_commands = list(string)
    build_commands   = list(string)
  }))
  default = {}
}

variable "user_dynamic_services" {
  description = "Map of user dynamic services to deploy"
  type = map(object({
    runtime           = string
    cpu              = number
    memory           = number
    github_repository = string
    github_branch    = string
    install_commands = list(string)
    build_commands   = list(string)
    start_command    = string
  }))
  default = {}
}

