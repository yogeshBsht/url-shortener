resource "aws_lb" "main" {
  name               = "urlshortener-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id
}

resource "aws_lb_target_group" "main" {
  name     = "urlshortener-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    path                = "/alb-health"
    healthy_threshold   = 5
    unhealthy_threshold = 3
    interval            = 30
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main.arn
  }
}

locals {
  asg_user_data = <<-EOF
    #!/bin/bash
    set -euxo pipefail
    exec > >(tee /var/log/user-data.log) 2>&1

    export AWS_DEFAULT_REGION=${var.region}
    ECR_REGISTRY="${local.ecr_registry}"
    S3_BUCKET="${aws_s3_bucket.config.bucket}"
    APP_DIR="/opt/app"

    if systemctl is-active --quiet apache2 2>/dev/null; then
      systemctl stop apache2
      systemctl disable apache2
    fi

    mkdir -p "$APP_DIR"
    cd "$APP_DIR"
    aws s3 cp "s3://$${S3_BUCKET}/app-config.tar.gz" ./app-config.tar.gz
    tar xzf app-config.tar.gz
    aws ssm get-parameter --name /urlshortener/env --with-decryption --query 'Parameter.Value' --output text > .env

    aws ecr get-login-password --region ${var.region} | docker login --username AWS --password-stdin "$${ECR_REGISTRY}"
    ECR_REGISTRY="$${ECR_REGISTRY}" IMAGE_TAG="latest" \
      docker compose -f docker-compose.app.yml -f docker-compose.app.prod.yml up -d
  EOF
}

resource "aws_launch_template" "app" {
  name_prefix   = "urlshortener-app-lt-"
  image_id      = var.golden_ami_id
  instance_type = "t3.small"
  key_name      = var.key_pair_name

  iam_instance_profile {
    name = aws_iam_instance_profile.asg_instance.name
  }

  network_interfaces {
    security_groups             = [aws_security_group.asg_instance.id]
    associate_public_ip_address = false
  }

  user_data = base64encode(local.asg_user_data)

  tag_specifications {
    resource_type = "instance"
    tags          = { Role = "app-server" }
  }
}

resource "aws_autoscaling_group" "app" {
  name                = "urlshortener-asg"
  vpc_zone_identifier = aws_subnet.private[*].id
  min_size            = var.asg_min_size
  max_size            = var.asg_max_size
  desired_capacity    = var.asg_desired_capacity

  launch_template {
    id      = aws_launch_template.app.id
    version = "$Latest"
  }

  target_group_arns        = [aws_lb_target_group.main.arn]
  health_check_type        = "ELB"
  health_check_grace_period = 60

  tag {
    key                 = "Role"
    value               = "app-server"
    propagate_at_launch = true
  }

  lifecycle {
    ignore_changes = [desired_capacity]
  }
}

resource "aws_autoscaling_policy" "requests_per_target" {
  name                   = "urlshortener-alb-request-tracking"
  autoscaling_group_name = aws_autoscaling_group.app.name
  policy_type            = "TargetTrackingScaling"

  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label         = "${aws_lb.main.arn_suffix}/${aws_lb_target_group.main.arn_suffix}"
    }
    target_value = 1000
  }
}
