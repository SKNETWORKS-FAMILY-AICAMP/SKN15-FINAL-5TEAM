# PostgreSQL Service

KIME Chat 프로젝트의 PostgreSQL 데이터베이스 설정 및 초기화 스크립트입니다.

## 구조

```
postgres/
├── init/                    # 초기화 스크립트 (자동 실행)
│   └── 01-init-database.sql # 데이터베이스, 스키마, 확장 설정
└── README.md
```

## 사용된 이미지

- **ankane/pgvector:latest**: PostgreSQL + pgvector 확장 포함
- pgvector: 벡터 임베딩 저장 및 유사도 검색 지원

## 초기화 스크립트

`init/` 폴더의 `.sql` 파일들은 컨테이너 최초 생성 시 자동으로 실행됩니다:

1. `01-init-database.sql`:
   - pgvector 확장 활성화
   - statedb, public 스키마 생성
   - 권한 설정

## Docker Compose 설정

```yaml
postgres:
  image: ankane/pgvector:latest
  volumes:
    - ./postgres/init:/docker-entrypoint-initdb.d
    - postgres_data:/var/lib/postgresql/data
  environment:
    POSTGRES_DB: kimedb
    POSTGRES_USER: kime
    POSTGRES_PASSWORD: ${DB_PASSWORD}
```

## 데이터베이스 접속

```bash
# 컨테이너 내부에서
docker exec -it kime-postgres psql -U kime -d kimedb

# 로컬에서
psql -h localhost -p 5432 -U kime -d kimedb
```

## 테이블 스키마

데이터베이스 테이블은 백엔드 애플리케이션이 자동으로 생성합니다:
- `backend/src/infrastructure/database/db_manager.py`의 `initialize_database()` 참조

주요 테이블:
- `statedb.sessions`: 세션 정보
- `statedb.dialogues`: 대화 내역
- `statedb.entities`: 엔티티 (캐릭터, 장소, 스킬 등)
- `statedb.entity_relationships`: 엔티티 간 관계
- `statedb.user_memories`: 사용자 장기 기억
- `statedb.training_logs`: 학습 데이터
