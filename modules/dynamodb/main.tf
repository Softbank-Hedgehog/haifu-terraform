resource "aws_dynamodb_table" "tables" {
  count = length(var.tables)
  
  name         = "${var.name_prefix}-${var.tables[count.index].name}"
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
  
  tags = merge(var.tags, {
    Name = "${var.name_prefix}-${var.tables[count.index].name}"
  })
}