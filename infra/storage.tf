resource "aws_s3_bucket" "config" {
  bucket = "urlshortener-infra-config-${var.account_id}"
}

resource "aws_s3_bucket_public_access_block" "config" {
  bucket                  = aws_s3_bucket.config.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "config" {
  bucket = aws_s3_bucket.config.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_object" "app_config" {
  bucket = aws_s3_bucket.config.id
  key    = "app-config.tar.gz"
  source = "${path.module}/../app-config.tar.gz"
  etag   = filemd5("${path.module}/../app-config.tar.gz")
}

resource "aws_s3_object" "monitoring_config" {
  bucket = aws_s3_bucket.config.id
  key    = "monitoring-config.tar.gz"
  source = "${path.module}/../monitoring-config.tar.gz"
  etag   = filemd5("${path.module}/../monitoring-config.tar.gz")
}

# NOTE: storing the .env content directly in Terraform state (even as a
# SecureString parameter) means the plaintext value lives in state too.
# Acceptable for this project's scope; for anything beyond a portfolio
# build, manage this parameter's value outside Terraform (console/CLI)
# and only manage the parameter's existence/policy here.
#
# templatefile() references aws_lb.main, aws_db_instance.main,
# aws_elasticache_replication_group.main, and aws_network_interface.monitoring
# directly, so Terraform's dependency graph creates this parameter only
# after those resources exist and their real endpoints are known — this
# is what collapses the previous two-phase (apply, then manually patch
# .env with real endpoints) into a single apply.
resource "aws_ssm_parameter" "env" {
  name = "/urlshortener/env"
  type = "SecureString"
  value = templatefile("${path.module}/templates/env.tftpl", {
    alb_dns_name            = aws_lb.main.dns_name
    rds_host                = aws_db_instance.main.address
    rds_db                  = aws_db_instance.main.db_name
    rds_master_username     = var.rds_master_username
    rds_master_password     = var.rds_master_password
    redis_host              = aws_elasticache_replication_group.main.primary_endpoint_address
    redis_auth_token        = var.redis_auth_token
    monitoring_private_ip   = aws_network_interface.monitoring.private_ip
    ecr_registry             = local.ecr_registry
    image_tag                = var.image_tag
    grafana_admin_user       = var.grafana_admin_user
    grafana_admin_password   = var.grafana_admin_password
    grafana_proxy_user       = var.grafana_proxy_user
    grafana_proxy_password   = var.grafana_proxy_password
  })

  lifecycle {
    ignore_changes = [value] # allow manual updates without drift on every plan
  }
}