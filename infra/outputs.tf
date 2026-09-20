output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "monitoring_private_ip" {
  value = aws_network_interface.monitoring.private_ip
}

output "rds_endpoint" {
  value = aws_db_instance.main.address
}

output "redis_endpoint" {
  value = aws_elasticache_replication_group.main.primary_endpoint_address
}
