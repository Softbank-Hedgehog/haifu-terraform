locals {
  role_policy_attachments = flatten([
    for role_idx, role in var.roles : [
      for policy_arn in role.managed_policy_arns : {
        role_index = role_idx
        policy_arn = policy_arn
      }
    ]
  ])

  custom_policy_attachments = flatten([
    for role_idx, role in var.roles : [
      for policy_name in role.custom_policy_names : {
        role_index   = role_idx
        policy_index = index([for p in var.custom_policies : p.name], policy_name)
      }
    ]
  ])
}