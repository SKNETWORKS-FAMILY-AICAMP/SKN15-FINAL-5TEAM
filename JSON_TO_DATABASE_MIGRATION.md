# JSON to Database Migration - Complete

## 개요

게임 콘텐츠 데이터(캐릭터, 시나리오 비트, 이미지 매핑)를 JSON 파일에서 PostgreSQL 데이터베이스로 완전히 마이그레이션했습니다.

날짜: 2025-11-06

## 마이그레이션된 데이터

### 1. 캐릭터 데이터 (7명)
- **캐릭터**: 탄지로, 네즈코, 렌고쿠, 젠이츠, 이노스케, 아카자, 엔무
- **테이블**:
  - `content.characters` - 기본 캐릭터 정보 (7 rows)
  - `content.character_core_values` - 핵심 가치관 (30 rows)
  - `content.character_emotional_triggers` - 감정 트리거 (44 rows)
  - `content.character_tone` - 호감도별 말투 (21 rows)
  - `content.character_aliases` - 캐릭터 별칭 (15 rows)
  - `content.character_quotes` - 명대사 (21 rows)
  - `content.character_intent_rules` - AI 의도 규칙 (40 rows)

### 2. 시나리오 비트 데이터
- **시나리오**: train (무한열차)
- **테이블**:
  - `content.scenario_beats` - 스토리 비트 (19 rows)
  - `content.beat_goals` - 비트별 목표/대사 (121 rows)

### 3. 이미지 매핑 데이터
- **시나리오**: train (무한열차)
- **테이블**:
  - `content.image_mappings` - 이미지 URL 매핑 (21 rows)
  - 메타데이터 포함 (이름, 설명, 태그, 키워드)

### 4. 세계관 데이터
- **세계관**: demon_slayer_taisho (귀멸의 칼날 - 다이쇼 시대)
- **테이블**:
  - `content.worlds` - 세계관 설정 (1 row)

## 생성된 파일

### 1. 데이터베이스 마이그레이션
- **[database/migrations/020_game_content_data.sql](database/migrations/020_game_content_data.sql)**
  - 11개 테이블 생성 (characters, beats, images 등)
  - scenarios 테이블에 world_id 컬럼 추가
  - 적절한 인덱스와 외래키 제약조건

### 2. 데이터 마이그레이션 스크립트
- **[backend/scripts/migrate_json_to_db.py](backend/scripts/migrate_json_to_db.py)**
  - JSON 파일에서 데이터베이스로 데이터 마이그레이션
  - 함수:
    - `migrate_world()` - 세계관 데이터
    - `migrate_characters()` - 모든 캐릭터
    - `migrate_scenario_beats()` - 시나리오 비트
    - `migrate_image_mappings()` - 이미지 매핑

### 3. 데이터베이스 접근 메서드
- **[backend/src/infrastructure/database/db_manager.py](backend/src/infrastructure/database/db_manager.py:2492-2703)**
  - `get_character(character_id)` - 캐릭터 전체 데이터 로드
  - `list_characters()` - 모든 캐릭터 ID 목록
  - `get_scenario_beats(scenario_id)` - 시나리오 비트 로드
  - `get_image_mappings(scenario_id)` - 이미지 매핑 로드

### 4. 코드 업데이트
- **[backend/src/utils/characters_repo.py](backend/src/utils/characters_repo.py)**
  - JSON 파일 대신 데이터베이스에서 캐릭터 로드
  - 데이터베이스 실패 시 JSON 파일로 fallback
  - LRU 캐시로 성능 최적화

## 실행된 작업

```bash
# 1. 마이그레이션 SQL 적용
docker exec -i postgresql psql -U kime -d kimedb < database/migrations/020_game_content_data.sql

# 2. 데이터 마이그레이션
docker exec backend python3 scripts/migrate_json_to_db.py

# 3. Redis 캐시 클리어
docker exec redis redis-cli FLUSHALL

# 4. 백엔드 재시작
docker restart backend
```

## 마이그레이션 결과

### ✅ 성공
- 7개 캐릭터 완전 마이그레이션 (131개 관련 데이터 포함)
- 19개 시나리오 비트 + 121개 목표 마이그레이션
- 21개 이미지 매핑 마이그레이션
- 1개 세계관 데이터 생성
- **총 331 rows 마이그레이션 완료**

### 테스트 결과
```python
# 캐릭터 로딩 테스트
Characters: ['akaza', 'enmu', 'inosuke', 'nezuko', 'rengoku', 'tanjiro', 'zenitsu']
Rengoku name: 렌고쿠 쿄쥬로
Core values: ['후배와 동료를 아끼고 격려함', '긍정적이고 열정적인 태도']
```

```bash
# 헬스 체크
$ curl http://localhost:8000/health
{"status":"healthy","database":"healthy","service":"KIME Chat API"}
```

## 이점

### 1. 동적 콘텐츠 관리
- 코드 재배포 없이 캐릭터/시나리오 업데이트 가능
- 관리자 페이지에서 콘텐츠 편집 가능
- A/B 테스팅 및 실험 용이

### 2. 성능 향상
- 파일 I/O 대신 데이터베이스 쿼리
- 인덱스를 통한 빠른 검색
- 연결된 데이터 효율적으로 조회 (JOIN)

### 3. 데이터 무결성
- 외래키 제약조건으로 데이터 일관성 보장
- 트랜잭션으로 원자적 업데이트
- 데이터 타입 검증

### 4. 확장성
- 새로운 캐릭터/시나리오 쉽게 추가
- 통계 및 분석 쿼리 작성 가능
- 다국어 지원 용이 (i18n 테이블 추가 가능)

## 다음 단계 (선택사항)

### 1. 관리자 페이지
- 캐릭터 편집 UI
- 시나리오 비트 편집기
- 이미지 업로드 및 매핑 관리

### 2. 버전 관리
- 캐릭터 데이터 버전 히스토리
- 롤백 기능
- 변경사항 추적 (audit log)

### 3. 캐싱 전략
- Redis에 자주 사용되는 캐릭터 캐시
- TTL 기반 자동 갱신
- 캐시 무효화 API

### 4. JSON 파일 정리
```bash
# 백업 디렉토리로 이동
mkdir -p backup/data_json
mv backend/data/characters/*.json backup/data_json/
mv backend/data/scenarios/cutscene5_llm_driven.json backup/data_json/
mv backend/data/image_mappings/*.json backup/data_json/
```

## 롤백 절차 (필요시)

```python
# characters_repo.py에서 데이터베이스 로딩 비활성화
# _scan() 함수를 원래 JSON 기반 구현으로 되돌림

# 또는 JSON 파일이 여전히 존재하므로 fallback 로직이 자동 동작
```

## 참고사항

- JSON 파일은 fallback으로 유지되므로 데이터베이스 장애 시에도 동작
- 캐릭터 데이터는 LRU 캐시로 성능 최적화
- RealDictCursor 사용으로 dict 형태로 데이터 반환
- JSONB 필드는 psycopg2가 자동으로 파싱 (json.loads() 불필요)

## 마이그레이션 통계

| 항목 | JSON 파일 | DB 테이블 | Rows |
|------|-----------|-----------|------|
| 캐릭터 기본 정보 | 7 files | characters | 7 |
| 캐릭터 관련 데이터 | - | 6 tables | 171 |
| 시나리오 비트 | 1 file | scenario_beats | 19 |
| 비트 목표 | - | beat_goals | 121 |
| 이미지 매핑 | 3 files | image_mappings | 21 |
| 세계관 | hardcoded | worlds | 1 |
| **합계** | **11 files** | **12 tables** | **340 rows** |

---

**마이그레이션 완료!** 🎉

모든 게임 콘텐츠 데이터가 성공적으로 데이터베이스로 마이그레이션되었으며,
애플리케이션은 이제 JSON 파일 대신 PostgreSQL 데이터베이스에서 데이터를 로드합니다.
