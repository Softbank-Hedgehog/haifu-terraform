resource "aws_rds_cluster" "main" {
  cluster_identifier      = "${var.name_prefix}-aurora"
  engine                  = var.engine
  engine_version          = var.engine_version
  availability_zones      = var.availability_zones
  database_name           = var.database_name
  master_username         = var.master_username
  master_password         = var.master_password
  backup_retention_period = var.backup_retention_period
  preferred_backup_window = var.preferred_backup_window
  db_subnet_group_name    = aws_db_subnet_group.main.name
  vpc_security_group_ids  = var.security_group_ids
  storage_encrypted       = var.storage_encrypted
  kms_key_id             = var.kms_key_id

  skip_final_snapshot       = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${var.name_prefix}-final-snapshot"

  tags = var.tags
}

resource "aws_rds_cluster_instance" "cluster_instances" {
  count              = var.instance_count
  identifier         = "${var.name_prefix}-aurora-${count.index}"
  cluster_identifier = aws_rds_cluster.main.id
  instance_class     = var.instance_class
  engine             = aws_rds_cluster.main.engine
  engine_version     = aws_rds_cluster.main.engine_version

  tags = var.tags
}