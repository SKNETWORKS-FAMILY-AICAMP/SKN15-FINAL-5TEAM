# Redis Service

KIME Chat 프로젝트의 Redis 캐시 서버 설정입니다.

## 구조

```
redis/
├── config/
│   └── redis.conf      # Redis 설정 파일
└── README.md
```

## 사용된 이미지

- **redis:7-alpine**: 경량화된 Redis 7.x

## 주요 설정

### 메모리 관리
- **maxmemory**: 256MB
- **maxmemory-policy**: allkeys-lru (LRU 방식으로 오래된 키 삭제)

### 데이터 영속성
- **RDB Snapshot**:
  - 900초마다 1개 이상 변경 시
  - 300초마다 10개 이상 변경 시
  - 60초마다 10000개 이상 변경 시
- **AOF**: 비활성화 (개발 환경)

### 네트워크
- **Port**: 6379
- **Bind**: 0.0.0.0 (Docker 네트워크 내부)

## Docker Compose 설정

```yaml
redis:
  image: redis:7-alpine
  volumes:
    - ./redis/config/redis.conf:/usr/local/etc/redis/redis.conf
    - redis_data:/data
  command: redis-server /usr/local/etc/redis/redis.conf
```

## Redis 접속

```bash
# 컨테이너 내부에서
docker exec -it kime-redis redis-cli

# 기본 명령어
> PING                    # 연결 확인
> KEYS *                  # 모든 키 조회
> GET session:abc123      # 특정 키 조회
> TTL session:abc123      # TTL 확인
> FLUSHALL                # 모든 데이터 삭제 (주의!)
```

## 사용 용도

1. **세션 캐싱**: 사용자 세션 상태 임시 저장
2. **대화 히스토리 캐싱**: 최근 대화 내용 빠른 조회
3. **임시 데이터**: API 응답 캐싱, Rate Limiting 등

## Backend 연동

Redis는 `backend/src/infrastructure/cache/cache_manager.py`를 통해 접근됩니다:

```python
from src.infrastructure.cache.cache_manager import CacheManager

cache = CacheManager(
    host="redis",  # Docker Compose 서비스 이름
    port=6379,
    db=0
)
```

## 프로덕션 고려사항

프로덕션 환경에서는 다음 설정을 추가하세요:

1. **비밀번호 설정**:
   ```conf
   requirepass your_strong_password
   ```

2. **AOF 활성화** (데이터 손실 방지):
   ```conf
   appendonly yes
   ```

3. **메모리 증가**:
   ```conf
   maxmemory 2gb
   ```

4. **복제 설정** (고가용성):
   - Redis Sentinel 또는 Redis Cluster 구성
