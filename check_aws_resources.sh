#!/bin/bash

# KIME Chat AWS 리소스 현황 확인
REGION="ap-northeast-2"

echo "======================================"
echo "📊 KIME Chat AWS 리소스 현황"
echo "======================================"
echo ""

echo "1️⃣  EC2 인스턴스"
echo "--------------------------------------"
aws ec2 describe-instances \
    --region $REGION \
    --filters "Name=tag:Name,Values=kime-*" \
    --query 'Reservations[].Instances[].[Tags[?Key==`Name`].Value|[0],InstanceId,InstanceType,State.Name,PrivateIpAddress,PublicIpAddress]' \
    --output table 2>/dev/null || echo "조회 실패 또는 인스턴스 없음"

echo ""
echo "2️⃣  Load Balancers (ALB)"
echo "--------------------------------------"
aws elbv2 describe-load-balancers \
    --region $REGION \
    --query 'LoadBalancers[?contains(LoadBalancerName, `kime`)].[LoadBalancerName,DNSName,State.Code]' \
    --output table 2>/dev/null || echo "조회 실패 또는 ALB 없음"

echo ""
echo "3️⃣  Target Groups"
echo "--------------------------------------"
aws elbv2 describe-target-groups \
    --region $REGION \
    --query 'TargetGroups[?contains(TargetGroupName, `kime`)].[TargetGroupName,Protocol,Port,HealthCheckPath]' \
    --output table 2>/dev/null || echo "조회 실패 또는 Target Group 없음"

echo ""
echo "4️⃣  RDS 데이터베이스"
echo "--------------------------------------"
aws rds describe-db-instances \
    --region $REGION \
    --query 'DBInstances[?contains(DBInstanceIdentifier, `kime`)].[DBInstanceIdentifier,DBInstanceClass,Engine,DBInstanceStatus,Endpoint.Address]' \
    --output table 2>/dev/null || echo "조회 실패 또는 RDS 없음"

echo ""
echo "5️⃣  ElastiCache (Redis/Valkey)"
echo "--------------------------------------"
aws elasticache describe-cache-clusters \
    --region $REGION \
    --query 'CacheClusters[?contains(CacheClusterId, `kime`)].[CacheClusterId,CacheNodeType,Engine,CacheClusterStatus]' \
    --output table 2>/dev/null || echo "조회 실패 또는 ElastiCache 없음"

echo ""
echo "6️⃣  Security Groups"
echo "--------------------------------------"
aws ec2 describe-security-groups \
    --region $REGION \
    --filters "Name=group-name,Values=kime-*" \
    --query 'SecurityGroups[].[GroupName,GroupId,Description]' \
    --output table 2>/dev/null || echo "조회 실패 또는 Security Group 없음"

echo ""
echo "7️⃣  VPC"
echo "--------------------------------------"
aws ec2 describe-vpcs \
    --region $REGION \
    --filters "Name=tag:Name,Values=kime-vpc" \
    --query 'Vpcs[].[Tags[?Key==`Name`].Value|[0],VpcId,CidrBlock,State]' \
    --output table 2>/dev/null || echo "조회 실패 또는 VPC 없음"

echo ""
echo "======================================"
echo "✅ 리소스 확인 완료"
echo "======================================"
