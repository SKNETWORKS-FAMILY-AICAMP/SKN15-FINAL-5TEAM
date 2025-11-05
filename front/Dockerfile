# ============================================================
# Stage 1: Builder - Node.js 빌드 스테이지
# ============================================================
FROM node:18-alpine as builder

# 메타데이터
LABEL stage=builder

# 작업 디렉토리
WORKDIR /app

# Vite 빌드 시 사용할 API 엔드포인트 설정
ARG VITE_API_URL
ARG VITE_API_BASE_URL
ENV VITE_API_URL=${VITE_API_URL:-http://localhost:8000}
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL:-http://localhost:8000}

# 의존성 파일만 먼저 복사 (캐시 활용)
COPY package.json package-lock.json ./

# 의존성 설치 (clean install로 정확한 버전 보장)
RUN npm ci --only=production=false

# 소스 코드 복사
COPY . .

# 프로덕션 빌드 (Vite)
# 빌드 시 환경변수는 .env.production에서 로드됨
RUN npm run build


# ============================================================
# Stage 2: Runtime - Nginx로 정적 파일 서빙
# ============================================================
FROM nginx:1.25-alpine

# 메타데이터 라벨
LABEL maintainer="KIME Team"
LABEL description="KIME Chat Frontend (React + Vite + TypeScript)"
LABEL version="1.0.0"

# Nginx 설정 파일 복사 (커스텀 설정)
COPY nginx.conf /etc/nginx/nginx.conf

# Builder stage에서 빌드된 정적 파일 복사
COPY --from=builder /app/dist /usr/share/nginx/html

# Non-root 사용자로 실행하기 위한 설정
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid

# 포트 노출
EXPOSE 80

# 헬스체크
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

# Non-root 사용자로 전환
USER nginx

# Nginx 실행 (데몬 모드 비활성화로 포그라운드 실행)
CMD ["nginx", "-g", "daemon off;"]
