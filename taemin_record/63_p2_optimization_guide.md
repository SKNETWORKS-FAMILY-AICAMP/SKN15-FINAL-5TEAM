# P2 중장기 성능 최적화 가이드

**작성일**: 2025-11-04
**대상**: KIME Chat Service
**난이도**: Medium ~ Advanced

이 문서는 P0, P1 즉시 개선 작업이 완료된 후 진행할 중장기 최적화 작업에 대한 가이드입니다.

---

## 📊 현재 상태

✅ **완료된 작업 (P0, P1)**:
- 중복 프로세스 정리
- 프로세스 관리 스크립트
- DB 커넥션 풀 최적화
- API 응답 시간 로깅

🔄 **다음 단계 (P2)**:
1. Redis 캐싱 강화
2. LLM Streaming 응답
3. 프론트엔드 번들 최적화
4. 동시 사용자 부하 테스트

---

## 1. Redis 캐싱 강화

### 목표
DB 조회 빈도가 높은 데이터를 Redis에 캐싱하여 응답 속도 향상

### 대상 데이터
- **시나리오 목록** (`GET /api/scenarios`) - 자주 조회, 거의 변경 안됨
- **시나리오 상세** (`GET /api/scenarios/{id}`) - 자주 조회
- **캐릭터 정보** - 정적 데이터

### 구현 방법

#### A. CacheManager 확장

현재 `backend/src/database/cache_manager.py`를 확장:

```python
# backend/src/database/cache_manager.py에 추가

class CacheManager:
    # ... 기존 코드 ...

    async def get_scenarios_cached(self, ttl: int = 300):
        """
        시나리오 목록 캐싱 (5분)

        Args:
            ttl: Time-to-live in seconds (default: 300 = 5분)
        """
        cache_key = "scenarios:all"

        # 1. Redis에서 조회
        cached = self.client.get(cache_key)
        if cached:
            return json.loads(cached)

        # 2. DB에서 조회
        from src.database.db_manager import DatabaseManager
        db = DatabaseManager()
        scenarios = db.get_all_scenarios()  # DB 메서드 호출

        # 3. Redis에 저장
        self.client.setex(
            cache_key,
            ttl,
            json.dumps(scenarios, ensure_ascii=False)
        )

        return scenarios

    async def get_scenario_cached(self, scenario_id: str, ttl: int = 600):
        """
        특정 시나리오 캐싱 (10분)
        """
        cache_key = f"scenario:{scenario_id}"

        cached = self.client.get(cache_key)
        if cached:
            return json.loads(cached)

        from src.database.db_manager import DatabaseManager
        db = DatabaseManager()
        scenario = db.get_scenario_by_id(scenario_id)

        if scenario:
            self.client.setex(
                cache_key,
                ttl,
                json.dumps(scenario, ensure_ascii=False)
            )

        return scenario

    def invalidate_scenarios_cache(self):
        """시나리오 캐시 무효화 (관리자가 시나리오 수정 시 호출)"""
        pattern = "scenarios:*"
        for key in self.client.scan_iter(match=pattern):
            self.client.delete(key)
```

#### B. API 엔드포인트 수정

`backend/api_server.py`에서 캐시 사용:

```python
# Before (캐시 없음)
@app.get("/api/scenarios")
async def get_scenarios():
    if not _hybrid_manager:
        return []
    scenarios = _hybrid_manager.db.get_all_scenarios()
    return scenarios

# After (캐시 적용)
@app.get("/api/scenarios")
async def get_scenarios():
    if not _hybrid_manager:
        return []

    # Redis 캐시 사용
    scenarios = await cache_manager.get_scenarios_cached(ttl=300)
    return scenarios
```

### 예상 효과

| 지표 | 개선 전 | 개선 후 | 개선율 |
|------|---------|---------|--------|
| 시나리오 목록 응답 시간 | ~100ms | ~5ms | **95% ↓** |
| DB 조회 빈도 | 매 요청 | 5분마다 | **99% ↓** |
| 동시 요청 처리 | 10 req/s | 200 req/s | **20배 ↑** |

### 테스트 방법

```bash
# 캐시 없을 때
time curl http://localhost:8000/api/scenarios

# 캐시 있을 때 (두 번째 요청)
time curl http://localhost:8000/api/scenarios

# 결과 비교
```

---

## 2. LLM Streaming 응답

### 목표
LLM 응답을 스트리밍 방식으로 제공하여 사용자 체감 속도 향상

### 현재 문제
- LLM 응답 완료까지 5-15초 대기
- 사용자는 빈 화면만 보고 있음
- 타임아웃 우려

### 구현 방법

#### A. Backend Streaming 지원

```python
# backend/api_server.py

from fastapi.responses import StreamingResponse
import asyncio

@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    """
    스트리밍 채팅 엔드포인트
    Server-Sent Events (SSE) 방식
    """
    async def generate_response():
        try:
            # LangGraph 워크플로우 생성
            workflow = create_workflow(...)

            # 스트리밍 방식으로 실행
            async for chunk in workflow.astream(initial_state):
                if "ai_response" in chunk:
                    # SSE 형식으로 전송
                    data = json.dumps({
                        "type": "message",
                        "content": chunk["ai_response"]
                    }, ensure_ascii=False)
                    yield f"data: {data}\n\n"
                    await asyncio.sleep(0)  # 이벤트 루프 양보

            # 완료 신호
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            error_data = json.dumps({
                "type": "error",
                "message": str(e)
            })
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"  # nginx 버퍼링 비활성화
        }
    )
```

#### B. Frontend EventSource 사용

```typescript
// front/src/services/api.ts

export async function chatStream(
  scenarioId: string,
  userInput: string,
  onMessage: (message: string) => void,
  onError: (error: string) => void,
  onComplete: () => void
) {
  const eventSource = new EventSource(
    `${API_URL}/api/chat/stream?` +
    `scenario_id=${scenarioId}&user_input=${encodeURIComponent(userInput)}`
  );

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === "message") {
      onMessage(data.content);
    } else if (data.type === "done") {
      eventSource.close();
      onComplete();
    } else if (data.type === "error") {
      eventSource.close();
      onError(data.message);
    }
  };

  eventSource.onerror = (error) => {
    eventSource.close();
    onError("Connection error");
  };

  return eventSource;  // 연결 객체 반환 (취소 가능)
}
```

#### C. React Component

```tsx
// front/src/components/ChatInterface.tsx

const [streamedMessage, setStreamedMessage] = useState("");

const handleSendMessage = async (message: string) => {
  setStreamedMessage("");  // 초기화

  const eventSource = await chatStream(
    scenarioId,
    message,
    // onMessage: 메시지 스트리밍
    (chunk) => {
      setStreamedMessage((prev) => prev + chunk);
    },
    // onError: 에러 처리
    (error) => {
      console.error("Stream error:", error);
      setError(error);
    },
    // onComplete: 완료 처리
    () => {
      console.log("Stream complete");
      // 최종 메시지 저장 등
    }
  );

  // 취소 버튼 처리
  return () => {
    eventSource.close();
  };
};
```

### 예상 효과

| 지표 | 개선 전 | 개선 후 | 사용자 체감 |
|------|---------|---------|-------------|
| 첫 응답 시간 | 5-15초 | 0.5-1초 | **90% 빠름** |
| 사용자 대기감 | 높음 | 낮음 | 타이핑 효과 |
| 타임아웃 위험 | 있음 | 없음 | 안정성 향상 |

---

## 3. 프론트엔드 번들 크기 최적화

### 목표
프론트엔드 로딩 시간 단축 및 네트워크 사용량 감소

### 분석 방법

```bash
# 1. 현재 번들 크기 확인
cd front
npm run build

# 출력 예시:
# dist/assets/index-abc123.js    523.45 kB
# dist/assets/vendor-def456.js   842.12 kB

# 2. 번들 분석 도구 설치
npm install -D vite-plugin-visualizer

# 3. vite.config.ts 수정
import { visualizer } from 'rollup-plugin-visualizer';

export default defineConfig({
  plugins: [
    react(),
    visualizer({
      filename: './dist/stats.html',
      open: true,
      gzipSize: true,
      brotliSize: true,
    })
  ],
});

# 4. 빌드 후 분석 결과 자동 오픈
npm run build
```

### 최적화 전략

#### A. 코드 스플리팅

```tsx
// Before: 모든 컴포넌트를 한번에 로드
import CharacterPage from './pages/CharacterPage';
import ChatPage from './pages/ChatPage';
import HomePage from './pages/HomePage';

// After: 라우트별로 분할 로드
const CharacterPage = lazy(() => import('./pages/CharacterPage'));
const ChatPage = lazy(() => import('./pages/ChatPage'));
const HomePage = lazy(() => import('./pages/HomePage'));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/character" element={<CharacterPage />} />
        <Route path="/chat" element={<ChatPage />} />
      </Routes>
    </Suspense>
  );
}
```

#### B. 라이브러리 최적화

```bash
# 큰 라이브러리 대체
npm uninstall moment     # 큰 라이브러리
npm install date-fns     # 가벼운 대안 (tree-shaking 지원)

# 또는
npm install dayjs        # 더 가벼운 대안
```

```tsx
// Before
import moment from 'moment';
const date = moment().format('YYYY-MM-DD');

// After
import { format } from 'date-fns';
const date = format(new Date(), 'yyyy-MM-dd');
```

#### C. 이미지 최적화

```tsx
// front/src/components/CharacterImage.tsx

interface CharacterImageProps {
  src: string;
  alt: string;
}

function CharacterImage({ src, alt }: CharacterImageProps) {
  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"  // 브라우저 네이티브 lazy loading
      decoding="async"  // 비동기 디코딩
    />
  );
}
```

### 목표

| 항목 | 현재 | 목표 | 개선 |
|------|------|------|------|
| 초기 JS 번들 | ~800KB | ~300KB | **62% ↓** |
| 초기 로딩 시간 | ~3s | ~1s | **66% ↓** |
| Lighthouse 점수 | 70 | 90+ | +20점 |

---

## 4. 동시 사용자 부하 테스트

### 목표
실제 운영 환경에서의 성능 한계 파악 및 병목 지점 발견

### 도구 선택

#### Apache Bench (간단)

```bash
# 설치 (macOS)
brew install httpd

# 테스트: 100명 동시 사용자, 1000 요청
ab -n 1000 -c 100 http://localhost:8000/api/scenarios

# 결과 예시:
# Requests per second:    245.32 [#/sec]
# Time per request:       407.631 [ms] (mean)
# Transfer rate:          89.45 [Kbytes/sec]
```

#### Locust (고급, 시나리오 기반)

```bash
# 설치
pip install locust

# 테스트 스크립트 작성
```

```python
# backend/locustfile.py

from locust import HttpUser, task, between

class KimeChatUser(HttpUser):
    wait_time = between(1, 3)  # 1-3초 대기

    @task(3)  # 가중치 3 (가장 많이 호출)
    def get_scenarios(self):
        """시나리오 목록 조회"""
        self.client.get("/api/scenarios")

    @task(2)  # 가중치 2
    def get_scenario_detail(self):
        """시나리오 상세 조회"""
        self.client.get("/api/scenarios/train")

    @task(1)  # 가중치 1 (가장 무거움)
    def send_chat(self):
        """채팅 메시지 전송"""
        self.client.post("/api/chat", json={
            "scenario_id": "train",
            "user_input": "안녕하세요",
            "user_name": f"테스트유저{self.user_id}"
        })

    def on_start(self):
        """사용자 시작 시 실행"""
        self.user_id = self.environment.runner.user_count
```

```bash
# 실행
locust -f locustfile.py --host=http://localhost:8000

# 웹 UI 접속: http://localhost:8089
# 동시 사용자 수, 증가 속도 설정 후 시작
```

### 성능 지표 모니터링

```bash
# 1. 시스템 리소스
htop  # CPU, 메모리 실시간 모니터링

# 2. DB 연결 수
docker exec kime-postgres psql -U kime -d kimedb -c \
  "SELECT count(*) FROM pg_stat_activity WHERE datname='kimedb';"

# 3. Redis 상태
docker exec kime-redis redis-cli INFO stats | grep ops_per_sec
```

### 병목 지점 식별

부하 테스트 중 확인할 사항:

1. **CPU 100%?** → 코드 최적화 필요
2. **메모리 부족?** → 메모리 누수 또는 캐시 크기 조정
3. **DB 연결 고갈?** → 커넥션 풀 크기 증가
4. **응답 시간 급증?** → 특정 API 엔드포인트 병목

---

## 5. 구현 우선순위

### Phase 1 (1주일)
1. ✅ **Redis 캐싱** - 즉시 효과, 구현 간단
2. ✅ **프론트엔드 분석** - 문제 파악

### Phase 2 (2주일)
3. 🔄 **프론트엔드 최적화** - 사용자 체감 큼
4. 🔄 **부하 테스트** - 현재 한계 파악

### Phase 3 (3-4주일)
5. 🔄 **LLM Streaming** - 구현 복잡, 효과 큼

---

## 6. 체크리스트

구현 전 확인 사항:

- [ ] P0, P1 작업 완료 확인
- [ ] Redis 정상 작동 확인
- [ ] 백업 브랜치 생성
- [ ] 로컬 환경 테스트 완료
- [ ] 성능 측정 베이스라인 설정
- [ ] 롤백 계획 수립

---

## 7. 참고 자료

### Redis 캐싱
- [Redis 공식 문서](https://redis.io/docs/)
- [Python Redis 라이브러리](https://redis-py.readthedocs.io/)

### LLM Streaming
- [FastAPI StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
- [Server-Sent Events (SSE)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)

### 프론트엔드 최적화
- [Vite Performance](https://vitejs.dev/guide/performance.html)
- [React Code Splitting](https://react.dev/reference/react/lazy)

### 부하 테스트
- [Locust 문서](https://docs.locust.io/)
- [Apache Bench 가이드](https://httpd.apache.org/docs/2.4/programs/ab.html)

---

**다음 업데이트**: 각 작업 완료 시 실제 성능 지표 추가
**담당자**: 개발팀
**예상 소요 기간**: 4-6주
