resource "aws_dynamodb_table" "tables" {
  count = length(var.tables)
  
  name         = var.name_prefix != null && var.name_prefix != "" ? "${var.name_prefix}-${var.tables[count.index].name}" : var.tables[count.index].name
  billing_mode = var.tables[count.index].billing_mode
  hash_key     = var.tables[count.index].hash_key
  range_key    = var.tables[count.index].range_key != "" ? var.tables[count.index].range_key : null
  
  dynamic "attribute" {
    for_each = var.tables[count.index].attributes
    content {
      name = attribute.value.name
      type = attribute.value.type
    }
  }
  
  dynamic "global_secondary_index" {
    for_each = var.tables[count.index].global_secondary_indexes
    content {
      name            = global_secondary_index.value.name
      hash_key        = global_secondary_index.value.hash_key
      range_key       = global_secondary_index.value.range_key
      projection_type = global_secondary_index.value.projection_type
    }
  }
  
  tags = merge(var.tags, {
    Name = var.name_prefix != null && var.name_prefix != "" ? "${var.name_prefix}-${var.tables[count.index].name}" : var.tables[count.index].name
  })
  

}