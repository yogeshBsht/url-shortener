variable "region" {
  default = "ap-south-1"
}

variable "account_id" {
  description = "AWS account ID, used to build the ECR registry URL"
  type        = string
}

variable "vpc_cidr" {
  default = "10.0.0.0/16"
}

variable "azs" {
  default = ["ap-south-1a", "ap-south-1b"]
}

variable "golden_ami_id" {
  description = "Pre-baked AMI with Docker + AWS CLI installed (see bake script)"
  type        = string
}

variable "key_pair_name" {
  description = "EC2 key pair for SSH fallback (Session Manager is the primary access path)"
  type        = string
  default     = null
}

variable "rds_master_username" {
  type      = string
  sensitive = true
}

variable "rds_master_password" {
  type      = string
  sensitive = true
}

variable "redis_auth_token" {
  type      = string
  sensitive = true
}

variable "image_tag" {
  default = "latest"
}

variable "grafana_admin_user" {
  type    = string
  default = "admin"
}

variable "grafana_admin_password" {
  type      = string
  sensitive = true
}

variable "grafana_proxy_user" {
  type    = string
  default = "admin"
}

variable "grafana_proxy_password" {
  type      = string
  sensitive = true
}

variable "asg_min_size" {
  default = 1
}

variable "asg_max_size" {
  default = 3
}

variable "asg_desired_capacity" {
  default = 1
}

variable "monitoring_private_ip" {
  description = "Fixed private IP for the monitoring instance, baked into frontend nginx config"
  type        = string
  default     = "10.0.10.10"
}