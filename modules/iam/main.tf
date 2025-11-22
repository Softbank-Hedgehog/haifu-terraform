resource "aws_iam_role" "main" {
  count = length(var.roles)
  name  = "${var.name_prefix}-${var.roles[count.index].name}"

  assume_role_policy = var.roles[count.index].assume_role_policy

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "managed" {
  count      = length(local.role_policy_attachments)
  role       = aws_iam_role.main[local.role_policy_attachments[count.index].role_index].name
  policy_arn = local.role_policy_attachments[count.index].policy_arn
}

resource "aws_iam_policy" "custom" {
  count  = length(var.custom_policies)
  name   = "${var.name_prefix}-${var.custom_policies[count.index].name}"
  policy = var.custom_policies[count.index].policy

  lifecycle {
    create_before_destroy = true
  }

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "custom" {
  count      = length(local.custom_policy_attachments)
  role       = aws_iam_role.main[local.custom_policy_attachments[count.index].role_index].name
  policy_arn = aws_iam_policy.custom[local.custom_policy_attachments[count.index].policy_index].arn
}