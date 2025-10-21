# Kime Chat Agent - Dockerfile
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필요한 도구 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 필요한 디렉토리 생성 (권한 문제 방지)
RUN mkdir -p /app/logs /app/data && \
    chmod -R 755 /app/logs /app/data

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \
    USE_LLM=true \
    DEBUG=false

# 기본 포트 (필요시)
EXPOSE 8000

# 헬스체크 (선택사항)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)"

# 실행 명령어
CMD ["python", "-u", "play.py"]
