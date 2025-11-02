#!/bin/bash
# Backend 배포 스크립트 for AWS EC2

set -e

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}KIME Backend Deployment to AWS${NC}"
echo -e "${GREEN}========================================${NC}"

# 설정
BASTION_IP="54.180.234.223"
BACKEND_1_IP="10.0.145.70"
BACKEND_2_IP="10.0.175.166"
KEY_PATH="$HOME/.ssh/kime-keypair.pem"
REMOTE_USER="ubuntu"
APP_DIR="/home/ubuntu/kime-backend"

# 인자 확인
if [ "$1" == "backend-1" ]; then
    TARGET_IP=$BACKEND_1_IP
    TARGET_NAME="backend-1"
elif [ "$1" == "backend-2" ]; then
    TARGET_IP=$BACKEND_2_IP
    TARGET_NAME="backend-2"
else
    echo -e "${RED}Usage: $0 [backend-1|backend-2]${NC}"
    exit 1
fi

echo -e "${YELLOW}Target: $TARGET_NAME ($TARGET_IP)${NC}"
echo ""

# Step 1: 코드 압축
echo -e "${GREEN}[1/6] 코드 압축 중...${NC}"
tar -czf /tmp/kime-backend.tar.gz \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='logs' \
    --exclude='.env' \
    --exclude='.env.local' \
    --exclude='test_*.py' \
    --exclude='demo_queries' \
    -C /Users/jtm427/Desktop/workspace/backend \
    .

echo -e "${GREEN}✓ 코드 압축 완료${NC}"

# Step 2: Bastion에 업로드
echo -e "${GREEN}[2/6] Bastion 호스트로 업로드 중...${NC}"
scp -i $KEY_PATH /tmp/kime-backend.tar.gz $REMOTE_USER@$BASTION_IP:/tmp/

echo -e "${GREEN}✓ Bastion 업로드 완료${NC}"

# Step 3: Backend로 전송 및 배포
echo -e "${GREEN}[3/6] Backend 서버로 전송 및 배포 중...${NC}"

ssh -i $KEY_PATH $REMOTE_USER@$BASTION_IP << 'BASTION_EOF'
#!/bin/bash
set -e

BACKEND_IP="'$TARGET_IP'"
KEY_PATH="/home/ubuntu/kime-keypair.pem"

# Bastion에서 Backend로 전송
echo "Backend 서버로 파일 전송 중..."
scp -i $KEY_PATH -o StrictHostKeyChecking=no /tmp/kime-backend.tar.gz ubuntu@$BACKEND_IP:/tmp/

# Backend 서버에서 배포 실행
echo "Backend 서버에서 배포 실행 중..."
ssh -i $KEY_PATH -o StrictHostKeyChecking=no ubuntu@$BACKEND_IP << 'BACKEND_EOF'
#!/bin/bash
set -e

APP_DIR="/home/ubuntu/kime-backend"

# 디렉토리 생성
mkdir -p $APP_DIR
cd $APP_DIR

# 코드 압축 해제
echo "코드 압축 해제 중..."
tar -xzf /tmp/kime-backend.tar.gz -C $APP_DIR

# Python 및 의존성 설치
echo "Python 환경 설정 중..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

# 가상환경 생성
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# 가상환경 활성화 및 의존성 설치
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 로그 디렉토리 생성
mkdir -p logs

echo "✓ Backend 서버 배포 완료"
BACKEND_EOF

BASTION_EOF

echo -e "${GREEN}✓ Backend 배포 완료${NC}"

# Step 4: 환경변수 파일 생성
echo -e "${GREEN}[4/6] 환경변수 설정 중...${NC}"

# .env 파일 내용 읽기
if [ ! -f ".env.production" ]; then
    echo -e "${RED}Error: .env.production 파일이 없습니다!${NC}"
    exit 1
fi

# 환경변수 파일을 Backend로 전송
scp -i $KEY_PATH .env.production $REMOTE_USER@$BASTION_IP:/tmp/kime-backend.env

ssh -i $KEY_PATH $REMOTE_USER@$BASTION_IP << 'ENV_EOF'
BACKEND_IP="'$TARGET_IP'"
KEY_PATH="/home/ubuntu/kime-keypair.pem"

scp -i $KEY_PATH -o StrictHostKeyChecking=no /tmp/kime-backend.env ubuntu@$BACKEND_IP:/home/ubuntu/kime-backend/.env
ENV_EOF

echo -e "${GREEN}✓ 환경변수 설정 완료${NC}"

# Step 5: Systemd 서비스 설정
echo -e "${GREEN}[5/6] Systemd 서비스 설정 중...${NC}"

cat > /tmp/kime-backend.service << 'SERVICE_EOF'
[Unit]
Description=KIME Backend API Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/kime-backend
Environment="PATH=/home/ubuntu/kime-backend/venv/bin"
ExecStart=/home/ubuntu/kime-backend/venv/bin/uvicorn api_server:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE_EOF

scp -i $KEY_PATH /tmp/kime-backend.service $REMOTE_USER@$BASTION_IP:/tmp/

ssh -i $KEY_PATH $REMOTE_USER@$BASTION_IP << 'SYSTEMD_EOF'
BACKEND_IP="'$TARGET_IP'"
KEY_PATH="/home/ubuntu/kime-keypair.pem"

ssh -i $KEY_PATH -o StrictHostKeyChecking=no ubuntu@$BACKEND_IP << 'BACKEND_SYSTEMD_EOF'
sudo mv /tmp/kime-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable kime-backend
sudo systemctl restart kime-backend
BACKEND_SYSTEMD_EOF

SYSTEMD_EOF

echo -e "${GREEN}✓ Systemd 서비스 설정 완료${NC}"

# Step 6: 상태 확인
echo -e "${GREEN}[6/6] 서비스 상태 확인 중...${NC}"

ssh -i $KEY_PATH $REMOTE_USER@$BASTION_IP << 'STATUS_EOF'
BACKEND_IP="'$TARGET_IP'"
KEY_PATH="/home/ubuntu/kime-keypair.pem"

echo "서비스 상태:"
ssh -i $KEY_PATH -o StrictHostKeyChecking=no ubuntu@$BACKEND_IP "sudo systemctl status kime-backend --no-pager | head -20"

echo ""
echo "Health check:"
sleep 5
ssh -i $KEY_PATH -o StrictHostKeyChecking=no ubuntu@$BACKEND_IP "curl -s http://localhost:8000/health || echo 'Health check endpoint not ready yet'"
STATUS_EOF

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}배포 완료!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${YELLOW}Target: $TARGET_NAME ($TARGET_IP)${NC}"

# 정리
rm -f /tmp/kime-backend.tar.gz /tmp/kime-backend.service

exit 0
