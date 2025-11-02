# Frontend & Backend 구체적 부족 사항

**Date**: 2025-11-03
**Purpose**: 코드 레벨에서 구체적으로 부족한 부분 파악

---

## 📊 전체 현황

### Frontend
- **총 라인 수**: 6,751줄
- **완성도**: 90%
- **주요 이슈**: API 연동 부분적, 환경변수 미설정

### Backend
- **총 라인 수**: 2,573줄 (api_server.py만)
- **완성도**: 95%
- **주요 이슈**: 미배포, CORS 설정

---

## 🚨 Frontend 부족 사항

### 1. CharacterPage.tsx - 하드코딩 데이터 사용 ❌

**현재 상태**:
```typescript
// CharacterPage.tsx:5-6
import scenariosData from '@/data/scenarios.json';

// Line 42
const scenarios = scenariosData as Record<string, ScenarioData>;
const scenario = characterId ? scenarios[characterId] : null;
```

**문제점**:
- ❌ API 대신 로컬 JSON 파일 사용
- ❌ 실시간 데이터 (좋아요, 조회수, 통계) 표시 불가
- ❌ HomePage는 API 연동 완료, CharacterPage는 미완

**필요한 수정**:
```typescript
// CharacterPage.tsx 수정 필요
import { apiClient, ScenarioCard } from '@/services/api';

export default function CharacterPage() {
  const [scenario, setScenario] = useState<ScenarioCard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadScenario = async () => {
      try {
        const data = await apiClient.getScenario(characterId);
        setScenario(data);
      } catch (error) {
        console.error('Failed to load scenario:', error);
      } finally {
        setLoading(false);
      }
    };
    loadScenario();
  }, [characterId]);

  // ... 나머지 코드
}
```

**영향도**: Medium
**소요 시간**: 20-30분

---

### 2. ChatPage.tsx - 하드코딩 데이터 사용 ❌

**현재 상태**:
```typescript
// ChatPage.tsx:9
import scenariosData from '@/data/scenarios.json';

// Line 81-82
const scenarios = scenariosData as Record<string, ScenarioData>;
const scenario = characterId ? scenarios[characterId] : null;
```

**문제점**:
- CharacterPage와 동일한 이슈
- 시나리오 제목만 표시용으로 사용 (치명적이진 않음)

**필요한 수정**:
```typescript
// ChatPage.tsx
const [scenarioTitle, setScenarioTitle] = useState<string>('');

useEffect(() => {
  const loadScenarioInfo = async () => {
    try {
      const data = await apiClient.getScenario(characterId);
      setScenarioTitle(data.title);
    } catch (error) {
      console.error('Failed to load scenario info:', error);
    }
  };
  loadScenarioInfo();
}, [characterId]);
```

**영향도**: Low (제목만 표시용)
**소요 시간**: 15분

---

### 3. 환경변수 파일 없음 ❌ (CRITICAL)

**현재 상태**:
```typescript
// utils/apiClient.ts:15
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// services/api.ts:10
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```

**문제점**:
- ❌ `.env` 파일이 존재하지 않음
- ❌ 모든 API 호출이 `localhost:8000`으로 향함
- ❌ AWS 배포 후에도 localhost 호출 → 실패

**필요한 파일**:
```bash
# front/.env (생성 필요)
VITE_API_URL=http://kime-alb-1043119388.ap-northeast-2.elb.amazonaws.com
VITE_API_BASE_URL=http://kime-alb-1043119388.ap-northeast-2.elb.amazonaws.com
VITE_CDN_URL=/images
```

**영향도**: CRITICAL
**소요 시간**: 5분

---

### 4. Frontend 빌드 파일 미배포 ❌ (CRITICAL)

**현재 상태**:
- Frontend EC2 인스턴스에 Nginx만 설치됨
- React 앱 (`dist/` 디렉토리)이 배포되지 않음
- 현재 ALB DNS 접속 시 Nginx default page만 표시

**필요한 작업**:
```bash
# 1. 환경변수 설정 후 빌드
cd front
npm run build  # dist/ 생성

# 2. dist를 Frontend EC2로 배포
scp -r dist/* ubuntu@54.180.234.223:/var/www/html/
scp -r dist/* ubuntu@3.39.251.70:/var/www/html/

# 3. Nginx 설정 (SPA 라우팅 지원)
# /etc/nginx/sites-available/default
location / {
  root /var/www/html;
  try_files $uri $uri/ /index.html;  # SPA fallback
}
```

**영향도**: CRITICAL
**소요 시간**: 30분

---

### 5. API Client 중복 설정 (코드 냄새)

**현재 상태**:
```typescript
// apiClient.ts:15
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// api.ts:10
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```

두 파일에서 다른 환경변수 이름 사용:
- `apiClient.ts` → `VITE_API_BASE_URL`
- `api.ts` → `VITE_API_URL`

**문제점**:
- ⚠️ 일관성 없음
- ⚠️ 혼란 가능성

**권장 수정**:
```typescript
// 모두 VITE_API_URL로 통일
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```

**영향도**: Low (기능적 문제는 없음)
**소요 시간**: 5분

---

## 🚨 Backend 부족 사항

### 1. CORS 설정 - localhost만 허용 ❌ (CRITICAL)

**현재 상태**:
```python
# api_server.py:86-94
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
    ],  # ❌ ALB DNS가 없음!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**문제점**:
- ❌ AWS ALB DNS에서 오는 요청을 거부함
- ❌ Frontend → Backend API 호출 실패 (CORS 에러)

**필요한 수정**:
```python
# Option 1: 환경변수로 관리 (권장)
import os

cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# .env.production에 추가
CORS_ORIGINS=http://localhost:5173,http://kime-alb-1043119388.ap-northeast-2.elb.amazonaws.com
```

**Option 2: 임시로 모두 허용 (테스트용)**
```python
allow_origins=["*"]  # 모든 origin 허용 (프로덕션 비권장)
```

**영향도**: CRITICAL
**소요 시간**: 10분

---

### 2. Backend 미배포 ❌ (CRITICAL)

**현재 상태**:
- Backend 코드가 로컬에만 존재
- AWS EC2 backend 인스턴스에 애플리케이션 없음
- API 엔드포인트 전부 404

**필요한 작업**:
```bash
# 배포 스크립트 실행
./backend/deploy_to_aws.sh backend-1
./backend/deploy_to_aws.sh backend-2
```

**배포 스크립트가 하는 일**:
1. Backend 코드 압축
2. Bastion (frontend-1) 경유하여 Backend EC2로 전송
3. Python 가상환경 생성
4. 의존성 설치 (requirements.txt)
5. .env.production 복사
6. Systemd 서비스 등록 (자동 시작)
7. uvicorn 시작

**영향도**: CRITICAL
**소요 시간**: 30-60분 (자동화됨)

---

### 3. Health Check Endpoint 구현 확인 ✅

**현재 상태**:
```python
# api_server.py:511
@app.get("/")
def root():
    return {"status": "healthy", "message": "KIME Chat API is running"}
```

**확인 결과**: ✅ 이미 구현되어 있음!

ALB가 `/health` 경로를 체크하도록 설정되어 있는데, 실제로는 `/`로 구현됨.

**필요한 조치**:
```python
# /health 엔드포인트 추가 (선택사항)
@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

또는 ALB Target Group 설정에서 Health Check Path를 `/`로 변경.

**영향도**: Low (이미 작동하는 엔드포인트 있음)
**소요 시간**: 5분

---

### 4. Database Migration 미실행 ❌ (CRITICAL)

**현재 상태**:
- RDS PostgreSQL 인스턴스 생성됨
- 하지만 테이블이 하나도 없음 (빈 DB)
- Migration SQL 파일 11개 실행 대기 중

**필요한 작업**:
```bash
# 로컬에서 RDS로 마이그레이션 실행
cd backend

for migration in database/migrations/*.sql; do
  echo "Running $migration..."
  PGPASSWORD=dev123 psql \
    -h kime-db.c1q6k80aex9v.ap-northeast-2.rds.amazonaws.com \
    -U kime \
    -d kimedb \
    -f $migration
done
```

**또는 Backend 서버 배포 후 실행**:
```bash
ssh to backend-1
cd /home/ubuntu/kime-backend
source venv/bin/activate

for migration in database/migrations/*.sql; do
  PGPASSWORD=dev123 psql -h kime-db... -U kime -d kimedb -f $migration
done
```

**영향도**: CRITICAL (DB 없으면 아무 것도 작동 안 함)
**소요 시간**: 10분

---

### 5. Scenario Seed Data 미삽입 ❌

**현재 상태**:
- `scenarios` 테이블이 생성되지만 데이터가 없음
- HomePage가 빈 배열 반환

**필요한 작업**:
```bash
# Seed 스크립트 실행
cd backend
python database/scripts/seed_scenarios.py
```

**seed_scenarios.py가 하는 일**:
- 6개 시나리오 삽입 (train, ending, tanjiro, etc.)
- scenario_statistics 초기화
- 이미지 경로, 태그, 설명 등 설정

**영향도**: High (HomePage가 비어 보임)
**소요 시간**: 5분

---

## 📋 우선순위별 작업 목록

### 🔴 P0 - 즉시 수행 (배포 전 필수)

| No | 작업 | 위치 | 시간 | 영향도 |
|----|------|------|------|--------|
| 1 | Frontend .env 파일 생성 | `front/.env` | 5분 | CRITICAL |
| 2 | Backend CORS 설정 수정 | `api_server.py` | 10분 | CRITICAL |
| 3 | RDS Migration 실행 | 로컬/Backend | 10분 | CRITICAL |
| 4 | Scenario Seed Data 삽입 | Backend | 5분 | HIGH |
| 5 | Backend 배포 | AWS | 60분 | CRITICAL |
| 6 | Frontend 빌드 & 배포 | AWS | 30분 | CRITICAL |

**Total**: 약 2시간

---

### 🟠 P1 - 배포 후 1주 내

| No | 작업 | 위치 | 시간 | 영향도 |
|----|------|------|------|--------|
| 7 | CharacterPage API 연동 | `CharacterPage.tsx` | 30분 | MEDIUM |
| 8 | ChatPage API 연동 | `ChatPage.tsx` | 15분 | LOW |
| 9 | API Client 환경변수 통일 | `apiClient.ts`, `api.ts` | 5분 | LOW |
| 10 | /health 엔드포인트 추가 | `api_server.py` | 5분 | LOW |

**Total**: 약 55분

---

## 🔍 상세 비교: HomePage vs CharacterPage

### HomePage (✅ 완료)

```typescript
// HomePage.tsx:35-77
useEffect(() => {
  const loadScenarios = async () => {
    try {
      const scenarios: ScenarioCard[] = currentUser
        ? await apiClient.getUserScenarios()  // ✅ API 사용
        : await apiClient.getScenarios();     // ✅ API 사용

      const transformedCharacters = scenarios.map(...);  // ✅ 변환
      setCharacters(transformedCharacters);

      if (currentUser) {
        const likedScenarioIds = scenarios
          .filter(s => s.is_liked)
          .map(s => s.scenario_id);
        setLikedCards(new Set(likedScenarioIds));  // ✅ 좋아요 상태
      }
    } catch (error) {
      setError('시나리오를 불러올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  };
  loadScenarios();
}, [currentUser]);
```

**특징**:
- ✅ API 연동 완료
- ✅ 로딩/에러 상태 처리
- ✅ 인증 사용자 구분 (좋아요 표시)
- ✅ 실시간 통계 표시

---

### CharacterPage (❌ 미완)

```typescript
// CharacterPage.tsx:40-43
const scenarios = scenariosData as Record<string, ScenarioData>;  // ❌ JSON 사용
const scenario = characterId ? scenarios[characterId] : null;

if (!scenario) {
  return <div>존재하지 않는 시나리오</div>;  // ❌ 에러만 처리
}
```

**특징**:
- ❌ 하드코딩 데이터 사용
- ❌ 로딩 상태 없음
- ❌ 에러 처리 부족
- ❌ 실시간 데이터 없음

**수정 필요 부분**:
1. `useEffect`로 API 호출
2. `useState`로 로딩/에러 관리
3. `apiClient.getScenario(id)` 사용
4. 실시간 좋아요/조회수 표시

---

## 📊 기능별 완성도 매트릭스

| 기능 | HomePage | CharacterPage | ChatPage | ChatInterface | RightSidebar |
|------|----------|---------------|----------|---------------|--------------|
| API 연동 | ✅ 100% | ❌ 0% | ⚠️ 50% | ✅ 100% | ✅ 100% |
| 로딩 상태 | ✅ 있음 | ❌ 없음 | ⚠️ 부분 | ✅ 있음 | ✅ 있음 |
| 에러 처리 | ✅ 있음 | ⚠️ 부분 | ⚠️ 부분 | ✅ 있음 | ✅ 있음 |
| 인증 연동 | ✅ 있음 | ❌ 없음 | ✅ 있음 | ✅ 있음 | ✅ 있음 |
| 실시간 데이터 | ✅ 있음 | ❌ 없음 | ❌ 없음 | ✅ 있음 | ✅ 있음 |

**전체 평균**: 약 75%

---

## 🎯 핵심 결론

### Frontend

**완료된 것**:
- ✅ HomePage: 100% API 연동
- ✅ ChatInterface: 100% API 연동
- ✅ RightSidebar: 100% API 연동
- ✅ 인증 시스템: 100% 완료
- ✅ API Client 라이브러리: 완벽 구현

**부족한 것**:
- ❌ CharacterPage: 하드코딩 데이터 (30분 수정)
- ❌ ChatPage: 하드코딩 데이터 (15분 수정)
- ❌ .env 파일 없음 (5분 생성) **← CRITICAL**
- ❌ 빌드 파일 미배포 (30분 배포) **← CRITICAL**

---

### Backend

**완료된 것**:
- ✅ 모든 API 엔드포인트 구현 (34개)
- ✅ 인증/인가 시스템 완료
- ✅ Database 스키마 완벽 설계
- ✅ LangGraph AI 엔진 구현
- ✅ 배포 스크립트 준비 완료

**부족한 것**:
- ❌ CORS 설정 (10분 수정) **← CRITICAL**
- ❌ AWS 배포 (60분 자동 실행) **← CRITICAL**
- ❌ RDS Migration 실행 (10분) **← CRITICAL**
- ❌ Seed Data 삽입 (5분) **← HIGH**

---

## 💡 Fast Track Plan (최소 시간으로 배포)

### Step 1: 로컬 준비 (20분)
1. Frontend `.env` 생성 (5분)
2. Backend CORS 수정 (10분)
3. Frontend 빌드 (5분)

### Step 2: Database 설정 (15분)
4. RDS Migration 실행 (10분)
5. Seed Data 삽입 (5분)

### Step 3: AWS 배포 (90분)
6. Backend 배포 (60분 - 자동)
7. Frontend 배포 (30분)

### Step 4: 검증 (15분)
8. Health Check
9. API 테스트
10. Frontend 동작 확인

**Total**: 약 2시간 20분

---

## 📁 관련 문서

1. [53_system_comprehensive_analysis.md](53_system_comprehensive_analysis.md) - 시스템 종합 분석
2. [52_backend_db_schema_analysis.md](52_backend_db_schema_analysis.md) - Backend/DB 정합성
3. [51_backend_deployment_preparation.md](51_backend_deployment_preparation.md) - 배포 준비
4. [50_phase2_complete_summary.md](50_phase2_complete_summary.md) - Phase 2 완료

---

**Document Status**: ✅ Complete
**Date**: 2025-11-03
**Next Action**: P0 작업 시작 (Frontend .env 생성)
