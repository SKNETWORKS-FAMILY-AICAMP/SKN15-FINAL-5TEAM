# DBeaver로 AWS RDS 연결하기

## 📊 DBeaver를 사용한 RDS 모니터링 가이드

DBeaver를 통해 AWS RDS PostgreSQL 데이터베이스에 연결하여 실시간으로 데이터를 확인하고 쿼리를 실행할 수 있습니다.

---

## 1️⃣ RDS 연결 정보

### Production (AWS RDS)
```
Host:     kime-db.c1q6k80aex9v.ap-northeast-2.rds.amazonaws.com
Port:     5432
Database: kimedb
Username: kime
Password: jnhzlsyihvxwfhvz
```

### Local Development (Docker PostgreSQL)
```
Host:     localhost
Port:     5433
Database: kimedb
Username: kime
Password: dev123
```

---

## 2️⃣ DBeaver 연결 설정 (단계별)

### Step 1: 새 연결 만들기

1. DBeaver 실행
2. 좌측 상단 **"새 데이터베이스 연결"** 버튼 클릭 (플러그 아이콘)
3. **PostgreSQL** 선택 → **다음**

### Step 2: 연결 정보 입력

**Main 탭:**
```
Server Host:    kime-db.c1q6k80aex9v.ap-northeast-2.rds.amazonaws.com
Port:           5432
Database:       kimedb
Username:       kime
Password:       jnhzlsyihvxwfhvz
```

- [x] **Show all databases** 체크 해제
- [x] **Save password** 체크 (선택사항)

### Step 3: SSL 설정 (RDS 필수)

**PostgreSQL 탭 → SSL:**
```
SSL mode:       require
```

또는 더 강력한 보안을 위해:
```
SSL mode:       verify-full
Root certificate: rds-ca-2019-root.pem (다운로드 필요)
```

**RDS SSL 인증서 다운로드:**
```bash
# 터미널에서 실행
curl -o ~/rds-ca-2019-root.pem https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
```

### Step 4: 연결 테스트

1. 좌측 하단 **"Test Connection"** 클릭
2. ✅ "Connected" 메시지 확인
3. **완료** 클릭

---

## 3️⃣ AWS 보안 그룹 설정 (중요!)

RDS에 연결하려면 **보안 그룹에서 당신의 IP를 허용**해야 합니다.

### AWS Console에서 설정:

1. **AWS Console → RDS → Databases → kime-db** 선택
2. **Connectivity & security** 탭
3. **VPC security groups** 클릭 (예: `kime-db-sg`)
4. **Inbound rules** → **Edit inbound rules**
5. **Add rule** 클릭:
   ```
   Type:        PostgreSQL
   Protocol:    TCP
   Port:        5432
   Source:      My IP (현재 내 IP 자동 입력)
   Description: DBeaver access from local machine
   ```
6. **Save rules**

### 현재 내 IP 확인:
```bash
curl ifconfig.me
```

### 주의사항:
- ⚠️ **0.0.0.0/0 (모든 IP 허용)은 절대 사용하지 마세요!** (보안 위험)
- ✅ 본인의 IP만 허용하세요
- 💡 IP가 바뀌면 다시 설정해야 합니다 (공유기 재시작, 카페 등)

---

## 4️⃣ DBeaver에서 데이터 확인

### 연결 후 탐색:

```
kime-db (연결)
 └── Databases
      └── kimedb
           └── Schemas
                ├── statedb          ← 메인 스키마
                │    ├── Tables
                │    │    ├── users
                │    │    ├── chat_sessions
                │    │    ├── dialogues
                │    │    ├── user_memories
                │    │    ├── user_progression
                │    │    ├── scenarios
                │    │    └── ...
                │    └── Views
                │         ├── v_user_progression_summary
                │         └── v_entity_relationships
                └── logdb            ← 로깅 스키마
                     └── Tables
                          └── training_logs
```

### 유용한 쿼리:

#### 1. 전체 사용자 목록
```sql
SELECT user_id, username, display_name, email, created_at
FROM statedb.users
ORDER BY created_at DESC;
```

#### 2. 사용자 진행도 요약
```sql
SELECT * FROM statedb.v_user_progression_summary
ORDER BY experience_points DESC;
```

#### 3. 최근 대화 기록
```sql
SELECT
    s.session_id,
    u.username,
    s.scenario_id,
    s.created_at,
    COUNT(d.dialogue_id) as message_count
FROM statedb.chat_sessions s
LEFT JOIN statedb.users u ON s.user_id = u.user_id
LEFT JOIN statedb.dialogues d ON s.session_id = d.session_id
GROUP BY s.session_id, u.username, s.scenario_id, s.created_at
ORDER BY s.created_at DESC
LIMIT 20;
```

#### 4. 사용자 장기 기억 확인
```sql
SELECT
    username,
    memory_key,
    memory_value,
    memory_type,
    created_at
FROM statedb.user_memories um
LEFT JOIN statedb.users u ON um.user_id = u.user_id
ORDER BY um.created_at DESC;
```

#### 5. 시나리오 목록
```sql
SELECT scenario_id, title_ko, description_ko, difficulty, is_active
FROM statedb.scenarios
ORDER BY display_order;
```

---

## 5️⃣ 데모 쿼리 파일 사용

프로젝트에 이미 준비된 쿼리 파일들이 있습니다:

### 위치: [backend/demo_queries/](backend/demo_queries/)

**DBeaver에서 실행하는 방법:**

1. DBeaver에서 **SQL Editor** 열기 (SQL 아이콘 클릭)
2. 파일 → 열기 → 쿼리 파일 선택
3. 실행 (Ctrl + Enter 또는 ▶️ 버튼)

**사용 가능한 쿼리 파일:**
- `01_session_check.sql` - 세션 확인
- `02_dialogues_check.sql` - 대화 기록 확인
- `03_training_logs_check.sql` - 학습 로그 확인
- `04_entities_check.sql` - 엔티티 확인
- `09_user_memories.sql` - 사용자 기억 확인
- `07_overall_stats.sql` - 전체 통계
- `08_performance_analysis.sql` - 성능 분석

---

## 6️⃣ 실시간 모니터링

### 자동 새로고침 설정:

1. 쿼리 실행 후 결과 탭에서
2. 우측 상단 **새로고침 아이콘 (🔄)** 클릭 → **Auto-refresh** 선택
3. 간격 설정: 5초, 10초, 30초 등

### 유용한 모니터링 쿼리:

#### 실시간 활성 세션
```sql
SELECT
    session_id,
    user_id,
    scenario_id,
    current_scene,
    created_at,
    NOW() - created_at as session_duration
FROM statedb.chat_sessions
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;
```

#### 최근 1시간 메시지 수
```sql
SELECT
    COUNT(*) as total_messages,
    COUNT(DISTINCT session_id) as active_sessions,
    COUNT(DISTINCT user_id) as active_users
FROM statedb.dialogues
WHERE timestamp > NOW() - INTERVAL '1 hour';
```

---

## 7️⃣ 트러블슈팅

### ❌ "Connection refused" 오류

**원인**: 보안 그룹이 내 IP를 차단함

**해결**:
1. AWS Console에서 보안 그룹 확인
2. 내 IP 추가 (위 3️⃣ 참고)
3. DBeaver에서 다시 연결

### ❌ "Timeout" 오류

**원인**: RDS가 Public Access를 허용하지 않음

**확인**:
```bash
# 터미널에서 연결 테스트
nc -zv kime-db.c1q6k80aex9v.ap-northeast-2.rds.amazonaws.com 5432
```

**해결**:
1. AWS Console → RDS → kime-db
2. **Modify** 클릭
3. **Connectivity → Public access** → **Yes** 선택
4. **Continue** → **Apply immediately** → **Modify DB instance**

### ❌ "SSL connection required" 오류

**해결**:
DBeaver 연결 설정 → PostgreSQL 탭 → SSL mode: `require` 설정

### ❌ "Authentication failed" 오류

**원인**: 잘못된 비밀번호

**확인**:
```bash
cat backend/.env.production | grep DB_PASSWORD
```

**해결**:
DBeaver에서 올바른 비밀번호 입력: `jnhzlsyihvxwfhvz`

---

## 8️⃣ 보안 베스트 프랙티스

### ✅ 해야 할 것:
- 본인 IP만 보안 그룹에 허용
- SSL 연결 사용 (`require` 이상)
- 비밀번호를 DBeaver에 저장하지 않기 (매번 입력)
- VPN 사용 시 VPN IP 허용

### ❌ 하지 말아야 할 것:
- 0.0.0.0/0 (모든 IP) 허용
- SSL 비활성화
- Public GitHub에 RDS 연결 정보 업로드
- 프로덕션 DB에서 `DELETE` 쿼리 실행 (조심!)

---

## 9️⃣ 추가 도구

### pgAdmin (대안)
PostgreSQL 전용 GUI 도구
```bash
# macOS 설치
brew install --cask pgadmin4
```

### psql (CLI)
터미널에서 직접 연결
```bash
PGPASSWORD=jnhzlsyihvxwfhvz psql \
  -h kime-db.c1q6k80aex9v.ap-northeast-2.rds.amazonaws.com \
  -p 5432 \
  -U kime \
  -d kimedb
```

### DataGrip (JetBrains)
유료이지만 강력한 DB 도구

---

## 📌 빠른 체크리스트

RDS 연결 전 확인사항:
- [ ] AWS 보안 그룹에 내 IP 추가
- [ ] RDS Public Access 활성화
- [ ] DBeaver PostgreSQL 드라이버 설치됨
- [ ] SSL mode 설정 (`require`)
- [ ] 연결 정보 정확히 입력
- [ ] Test Connection 성공

---

**작성일**: 2025-11-03
**RDS 엔드포인트**: kime-db.c1q6k80aex9v.ap-northeast-2.rds.amazonaws.com
**포트**: 5432
**데이터베이스**: kimedb
