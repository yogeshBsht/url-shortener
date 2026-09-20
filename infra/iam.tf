data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

# ---- ASG instance role ----
resource "aws_iam_role" "asg_instance" {
  name               = "urlshortener-asg-instance-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

resource "aws_iam_role_policy_attachment" "asg_ecr" {
  role       = aws_iam_role.asg_instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_role_policy_attachment" "asg_ssm_core" {
  role       = aws_iam_role.asg_instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "asg_inline" {
  name = "urlshortener-asg-inline-policy"
  role = aws_iam_role.asg_instance.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameter", "ssm:GetParameters"]
        Resource = "arn:aws:ssm:${var.region}:${var.account_id}:parameter/urlshortener/*"
      },
      { Effect = "Allow", Action = ["kms:Decrypt"], Resource = "*" },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "${aws_s3_bucket.config.arn}/*"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "asg_instance" {
  name = "urlshortener-asg-instance-profile"
  role = aws_iam_role.asg_instance.name
}

# ---- Monitoring instance role ----
resource "aws_iam_role" "monitoring" {
  name               = "urlshortener-monitoring-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

resource "aws_iam_role_policy_attachment" "monitoring_ecr" {
  role       = aws_iam_role.monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_role_policy_attachment" "monitoring_ssm_core" {
  role       = aws_iam_role.monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "monitoring_inline" {
  name = "urlshortener-monitoring-inline-policy"
  role = aws_iam_role.monitoring.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameter", "ssm:GetParameters"]
        Resource = "arn:aws:ssm:${var.region}:${var.account_id}:parameter/urlshortener/*"
      },
      { Effect = "Allow", Action = ["kms:Decrypt"], Resource = "*" },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "${aws_s3_bucket.config.arn}/*"
      },
      { Effect = "Allow", Action = ["ec2:DescribeInstances"], Resource = "*" }
    ]
  })
}

resource "aws_iam_instance_profile" "monitoring" {
  name = "urlshortener-monitoring-profile"
  role = aws_iam_role.monitoring.name
}
