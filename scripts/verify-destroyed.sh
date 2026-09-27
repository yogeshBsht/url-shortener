#!/bin/bash
# verify-destroyed.sh — confirms Phase 3 AWS resources are actually gone,
# independent of what Terraform's own state file claims.
# chmod +x verify-destroyed.sh
# ./verify-destroyed.sh

set -uo pipefail

REGION="ap-south-1"
PROJECT="urlshortener"
FAIL=0

check() {
  local label="$1"
  local count="$2"
  if [ "$count" -eq 0 ]; then
    echo "OK   - $label: none found"
  else
    echo "FAIL - $label: $count resource(s) still present"
    FAIL=1
  fi
}

echo "=== Terraform state ==="
STATE_COUNT=$(terraform -chdir=infra state list 2>/dev/null | wc -l)
check "Terraform-tracked resources" "$STATE_COUNT"

echo ""
echo "=== EC2 instances ==="
COUNT=$(aws ec2 describe-instances --region "$REGION" \
  --filters "Name=tag:Name,Values=${PROJECT}-*" "Name=instance-state-name,Values=pending,running,stopping,stopped" \
  --query 'Reservations[].Instances[].InstanceId' --output text | wc -w)
check "EC2 instances (non-terminated)" "$COUNT"

echo ""
echo "=== Auto Scaling Group ==="
COUNT=$(aws autoscaling describe-auto-scaling-groups --region "$REGION" \
  --query "AutoScalingGroups[?contains(AutoScalingGroupName, '${PROJECT}')].AutoScalingGroupName" --output text | wc -w)
check "Auto Scaling Groups" "$COUNT"

echo ""
echo "=== Load Balancer ==="
COUNT=$(aws elbv2 describe-load-balancers --region "$REGION" \
  --query "LoadBalancers[?contains(LoadBalancerName, '${PROJECT}')].LoadBalancerArn" --output text 2>/dev/null | wc -w)
check "Application Load Balancers" "$COUNT"

echo ""
echo "=== RDS ==="
COUNT=$(aws rds describe-db-instances --region "$REGION" \
  --query "DBInstances[?contains(DBInstanceIdentifier, '${PROJECT}')].DBInstanceIdentifier" --output text 2>/dev/null | wc -w)
check "RDS instances" "$COUNT"

echo ""
echo "=== ElastiCache ==="
COUNT=$(aws elasticache describe-replication-groups --region "$REGION" \
  --query "ReplicationGroups[?contains(ReplicationGroupId, '${PROJECT}')].ReplicationGroupId" --output text 2>/dev/null | wc -w)
check "ElastiCache replication groups" "$COUNT"

echo ""
echo "=== VPC Endpoints ==="
COUNT=$(aws ec2 describe-vpc-endpoints --region "$REGION" \
  --filters "Name=tag:Name,Values=${PROJECT}-*" "Name=vpc-endpoint-state,Values=available,pending" \
  --query 'VpcEndpoints[].VpcEndpointId' --output text | wc -w)
check "VPC endpoints" "$COUNT"

echo ""
echo "=== VPC ==="
COUNT=$(aws ec2 describe-vpcs --region "$REGION" \
  --filters "Name=tag:Name,Values=${PROJECT}-vpc" \
  --query 'Vpcs[].VpcId' --output text | wc -w)
check "VPCs" "$COUNT"

echo ""
echo "=== IAM roles ==="
COUNT=$(aws iam list-roles --query "Roles[?contains(RoleName, '${PROJECT}')].RoleName" --output text | wc -w)
check "IAM roles" "$COUNT"

echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "All checked resource types are clear."
else
  echo "Some resources are still present — review the FAIL lines above."
fi
echo ""
echo "Note: ECR images, the golden AMI, and S3/SSM (if you chose to keep"
echo "them) are NOT checked here — they're deliberately outside Terraform's"
echo "destroy scope and cost negligibly to leave in place."
echo ""
echo "Billing reflects with a lag (often 24h+); this script confirms"
echo "resource existence, not that charges have stopped accruing."

exit $FAIL