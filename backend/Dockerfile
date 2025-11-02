# ============================================================
# Stage 1: Builder - 의존성 설치 및 빌드
# ============================================================
FROM python:3.10-slim as builder

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 빌드 도구 설치
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 파일 복사
COPY requirements.txt .

# 의존성을 /install 디렉토리에 설치 (캐시 활용)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt


# ============================================================
# Stage 2: Runtime - 최종 실행 이미지 (경량화)
# ============================================================
FROM python:3.10-slim

# 메타데이터 라벨
LABEL maintainer="KIME Team"
LABEL description="KIME Chat Backend API Server (FastAPI + LangGraph)"
LABEL version="1.0.0"

# 작업 디렉토리
WORKDIR /app

# 런타임 시스템 패키지 설치 (최소한만)
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Builder stage에서 설치된 Python 패키지 복사
COPY --from=builder /install /usr/local

# Non-root 사용자 생성 (보안)
RUN groupadd -r kime && useradd -r -g kime kime

# 애플리케이션 코드 복사
COPY --chown=kime:kime . .

# 필요한 디렉토리 생성 및 권한 설정
RUN mkdir -p /app/logs /app/data /app/uploads && \
    chown -R kime:kime /app/logs /app/data /app/uploads && \
    chmod -R 755 /app/logs /app/data /app/uploads

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    USE_LLM=true \
    DEBUG=false \
    PORT=8000

# 포트 노출
EXPOSE 8000

# 헬스체크 (FastAPI /health 엔드포인트 기준)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Non-root 사용자로 전환
USER kime

# 실행 명령어 (Uvicorn으로 FastAPI 실행)
CMD ["python", "-m", "uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
