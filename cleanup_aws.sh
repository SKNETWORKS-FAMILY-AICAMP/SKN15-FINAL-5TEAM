#!/bin/bash

# KIME Chat AWS 리소스 정리 스크립트
# 실행 전 확인: AWS CLI 설정 및 권한 확인

set -e

REGION="ap-northeast-2"

echo "🗑️  KIME Chat AWS 리소스 삭제 시작..."
echo "Region: $REGION"
echo ""
echo "⚠️  이 작업은 되돌릴 수 없습니다!"
read -p "계속하시겠습니까? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "취소되었습니다."
    exit 0
fi

echo ""
echo "======================================"
echo "1️⃣  EC2 인스턴스 종료"
echo "======================================"

# Frontend-1 종료
FRONTEND_1_ID=$(aws ec2 describe-instances \
    --region $REGION \
    --filters "Name=tag:Name,Values=kime-frontend-1" "Name=instance-state-name,Values=running" \
    --query 'Reservations[0].Instances[0].InstanceId' \
    --output text 2>/dev/null || echo "")

if [ "$FRONTEND_1_ID" != "" ] && [ "$FRONTEND_1_ID" != "None" ]; then
    echo "Frontend-1 종료 중... ($FRONTEND_1_ID)"
    aws ec2 terminate-instances --region $REGION --instance-ids $FRONTEND_1_ID
else
    echo "Frontend-1을 찾을 수 없습니다."
fi

# Backend-1 종료
BACKEND_1_ID=$(aws ec2 describe-instances \
    --region $REGION \
    --filters "Name=tag:Name,Values=kime-backend-1" "Name=instance-state-name,Values=running" \
    --query 'Reservations[0].Instances[0].InstanceId' \
    --output text 2>/dev/null || echo "")

if [ "$BACKEND_1_ID" != "" ] && [ "$BACKEND_1_ID" != "None" ]; then
    echo "Backend-1 종료 중... ($BACKEND_1_ID)"
    aws ec2 terminate-instances --region $REGION --instance-ids $BACKEND_1_ID
else
    echo "Backend-1을 찾을 수 없습니다."
fi

echo "EC2 인스턴스 종료 대기 중... (30초)"
sleep 30

echo ""
echo "======================================"
echo "2️⃣  ALB 삭제"
echo "======================================"

ALB_ARN=$(aws elbv2 describe-load-balancers \
    --region $REGION \
    --query 'LoadBalancers[?contains(LoadBalancerName, `kime-alb`)].LoadBalancerArn' \
    --output text 2>/dev/null || echo "")

if [ "$ALB_ARN" != "" ]; then
    echo "ALB 삭제 중... ($ALB_ARN)"
    aws elbv2 delete-load-balancer --region $REGION --load-balancer-arn $ALB_ARN
    echo "ALB 삭제 대기 중... (60초)"
    sleep 60
else
    echo "ALB를 찾을 수 없습니다."
fi

echo ""
echo "======================================"
echo "3️⃣  Target Groups 삭제"
echo "======================================"

# Backend Target Group
BACKEND_TG_ARN=$(aws elbv2 describe-target-groups \
    --region $REGION \
    --query 'TargetGroups[?contains(TargetGroupName, `kime-backend`)].TargetGroupArn' \
    --output text 2>/dev/null || echo "")

if [ "$BACKEND_TG_ARN" != "" ]; then
    echo "Backend Target Group 삭제 중..."
    aws elbv2 delete-target-group --region $REGION --target-group-arn $BACKEND_TG_ARN
fi

# Frontend Target Group
FRONTEND_TG_ARN=$(aws elbv2 describe-target-groups \
    --region $REGION \
    --query 'TargetGroups[?contains(TargetGroupName, `kime-frontend`)].TargetGroupArn' \
    --output text 2>/dev/null || echo "")

if [ "$FRONTEND_TG_ARN" != "" ]; then
    echo "Frontend Target Group 삭제 중..."
    aws elbv2 delete-target-group --region $REGION --target-group-arn $FRONTEND_TG_ARN
fi

echo ""
echo "======================================"
echo "4️⃣  RDS 데이터베이스 삭제"
echo "======================================"

RDS_ID=$(aws rds describe-db-instances \
    --region $REGION \
    --query 'DBInstances[?contains(DBInstanceIdentifier, `kime-db`)].DBInstanceIdentifier' \
    --output text 2>/dev/null || echo "")

if [ "$RDS_ID" != "" ]; then
    echo "⚠️  RDS 삭제 중... 최종 스냅샷 생략 ($RDS_ID)"
    aws rds delete-db-instance \
        --region $REGION \
        --db-instance-identifier $RDS_ID \
        --skip-final-snapshot \
        --delete-automated-backups
    echo "RDS 삭제가 시작되었습니다 (완료까지 5-10분 소요)"
else
    echo "RDS를 찾을 수 없습니다."
fi

echo ""
echo "======================================"
echo "5️⃣  ElastiCache 삭제"
echo "======================================"

REDIS_ID=$(aws elasticache describe-cache-clusters \
    --region $REGION \
    --query 'CacheClusters[?contains(CacheClusterId, `kime-redis`)].CacheClusterId' \
    --output text 2>/dev/null || echo "")

if [ "$REDIS_ID" != "" ]; then
    echo "ElastiCache 삭제 중... ($REDIS_ID)"
    aws elasticache delete-cache-cluster \
        --region $REGION \
        --cache-cluster-id $REDIS_ID
    echo "ElastiCache 삭제가 시작되었습니다"
else
    echo "ElastiCache를 찾을 수 없습니다."
fi

echo ""
echo "======================================"
echo "⏳ 주요 리소스 삭제 완료"
echo "======================================"
echo ""
echo "📝 추가 정리 (수동):"
echo "   1. Security Groups (의존성이 해제되면 삭제 가능)"
echo "   2. VPC 및 서브넷 (모든 리소스 삭제 후)"
echo "   3. Key Pair (필요시)"
echo ""
echo "RDS와 ElastiCache는 삭제 완료까지 5-10분 소요됩니다."
echo "AWS Console에서 상태를 확인하세요."
echo ""
echo "✅ 삭제 스크립트 실행 완료!"
