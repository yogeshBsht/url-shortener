locals {
  ecr_registry = "${var.account_id}.dkr.ecr.${var.region}.amazonaws.com"

  monitoring_user_data = <<-EOF
    #!/bin/bash
    set -euxo pipefail
    exec > >(tee /var/log/user-data.log) 2>&1

    export AWS_DEFAULT_REGION=${var.region}
    ECR_REGISTRY="${local.ecr_registry}"
    S3_BUCKET="${aws_s3_bucket.config.bucket}"
    APP_DIR="/opt/app"

    mkdir -p "$APP_DIR"
    cd "$APP_DIR"
    aws s3 cp "s3://$${S3_BUCKET}/monitoring-config.tar.gz" ./monitoring-config.tar.gz
    tar xzf monitoring-config.tar.gz
    aws ssm get-parameter --name /urlshortener/env --with-decryption --query 'Parameter.Value' --output text > .env

    aws ecr get-login-password --region ${var.region} | docker login --username AWS --password-stdin "$${ECR_REGISTRY}"
    ECR_REGISTRY="$${ECR_REGISTRY}" \
      docker compose -f docker-compose.monitoring.yml -f docker-compose.monitoring.prod.yml up -d
  EOF
}

resource "aws_network_interface" "monitoring" {
  subnet_id       = aws_subnet.private[0].id
  private_ips     = [var.monitoring_private_ip]
  security_groups = [aws_security_group.monitoring.id]
  tags            = { Name = "urlshortener-monitoring-eni" }
}

resource "aws_instance" "monitoring" {
  ami           = var.golden_ami_id
  instance_type = "t3.small"
  key_name      = var.key_pair_name

  network_interface {
    network_interface_id = aws_network_interface.monitoring.id
    device_index          = 0
  }

  iam_instance_profile = aws_iam_instance_profile.monitoring.name
  user_data            = base64encode(local.monitoring_user_data)
  user_data_replace_on_change = true

  tags = { Name = "urlshortener-monitoring" }
}
