output "table_names" {
  description = "DynamoDB table names"
  value       = { for i, table in var.tables : table.name => aws_dynamodb_table.tables[i].name }
}

output "table_arns" {
  description = "DynamoDB table ARNs"
  value       = { for i, table in var.tables : table.name => aws_dynamodb_table.tables[i].arn }
}