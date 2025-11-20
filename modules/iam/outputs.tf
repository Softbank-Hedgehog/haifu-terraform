output "role_arns" {
  description = "IAM role ARNs"
  value       = { for idx, role in aws_iam_role.main : var.roles[idx].name => role.arn }
}

output "role_names" {
  description = "IAM role names"
  value       = { for idx, role in aws_iam_role.main : var.roles[idx].name => role.name }
}

output "policy_arns" {
  description = "Custom policy ARNs"
  value       = { for idx, policy in aws_iam_policy.custom : var.custom_policies[idx].name => policy.arn }
}