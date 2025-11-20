variable "name_prefix" {
  description = "Name prefix for resources"
  type        = string
}

variable "engine" {
  description = "Database engine"
  type        = string
  default     = "aurora-mysql"
}

variable "engine_version" {
  description = "Database engine version"
  type        = string
  default     = "8.0.mysql_aurora.3.02.0"
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
}

variable "database_name" {
  description = "Database name"
  type        = string
}

variable "master_username" {
  description = "Master username"
  type        = string
  default     = "admin"
}

variable "master_password" {
  description = "Master password"
  type        = string
  sensitive   = true
}

variable "backup_retention_period" {
  description = "Backup retention period"
  type        = number
  default     = 7
}

variable "preferred_backup_window" {
  description = "Preferred backup window"
  type        = string
  default     = "07:00-09:00"
}

variable "subnet_ids" {
  description = "Subnet IDs"
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security group IDs"
  type        = list(string)
}

variable "storage_encrypted" {
  description = "Storage encrypted"
  type        = bool
  default     = true
}

variable "kms_key_id" {
  description = "KMS key ID"
  type        = string
  default     = null
}

variable "skip_final_snapshot" {
  description = "Skip final snapshot"
  type        = bool
  default     = false
}

variable "instance_count" {
  description = "Number of instances"
  type        = number
  default     = 2
}

variable "instance_class" {
  description = "Instance class"
  type        = string
  default     = "db.r6g.large"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}