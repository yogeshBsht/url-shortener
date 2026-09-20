resource "aws_db_subnet_group" "main" {
  name       = "urlshortener-rds-subnet-group"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_parameter_group" "main" {
  name   = "urlshortener-pg15-custom"
  family = "postgres15"

  parameter {
    name         = "shared_preload_libraries"
    value        = "pg_stat_statements"
    apply_method = "pending-reboot"
  }
}

resource "aws_db_instance" "main" {
  identifier             = "urlshortener-db"
  engine                 = "postgres"
  engine_version         = "15"
  instance_class         = "db.t3.micro"
  allocated_storage      = 20
  storage_type           = "gp2"
  db_name                = "urlshortener"
  username               = var.rds_master_username
  password               = var.rds_master_password
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  parameter_group_name   = aws_db_parameter_group.main.name
  publicly_accessible    = false
  multi_az               = false
  skip_final_snapshot    = true # deliberate: this project tears down/rebuilds for cost control
  apply_immediately      = true
}
