resource "aws_elasticache_subnet_group" "main" {
  name       = "urlshortener-cache-subnet-group"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_elasticache_parameter_group" "main" {
  name   = "urlshortener-redis7-custom"
  family = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }
}

# Note: encryption in transit + AUTH token require aws_elasticache_replication_group
# rather than the plain aws_elasticache_cluster resource, even for a single node.
resource "aws_elasticache_replication_group" "main" {
  replication_group_id       = "urlshortener-cache"
  description                = "URL shortener cache - single node, cluster mode disabled"
  engine                     = "redis"
  engine_version             = "7.0"
  node_type                  = "cache.t3.micro"
  num_cache_clusters         = 1
  parameter_group_name       = aws_elasticache_parameter_group.main.name
  subnet_group_name          = aws_elasticache_subnet_group.main.name
  security_group_ids         = [aws_security_group.elasticache.id]
  automatic_failover_enabled = false
  multi_az_enabled           = false
  transit_encryption_enabled = true
  at_rest_encryption_enabled = true
  auth_token                 = var.redis_auth_token
}
