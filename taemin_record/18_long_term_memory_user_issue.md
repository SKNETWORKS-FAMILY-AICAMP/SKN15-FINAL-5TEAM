# 18. 장기기억 시스템 User ID 문제 분석

**작성일**: 2025-10-30
**상태**: 🔴 심각한 설계 문제 발견

## 🚨 핵심 문제

**사용자 질문**: "장기기억을 유저별로 하려면 user_id가 필요할텐데 그게 없네??"

**분석 결과**: **정확한 지적입니다!** 현재 구조는 세션별 장기기억만 가능하고, 유저별 장기기억은 불가능합니다.

## 📊 현재 구조 분석

### 1. Sessions 테이블 구조

```sql
\d+ statedb.sessions

-- 관련 컬럼:
user_id              UUID         NULL 허용    -- 사용자 ID (외래 키)
user_name            VARCHAR(255) NULL 허용    -- 사용자 이름 (단순 문자열)
conversation_summary TEXT         기본값 ''   -- 대화 요약
summary_updated_at   TIMESTAMP    NULL 허용    -- 마지막 요약 시간
summary_turn_count   INTEGER      기본값 0     -- 요약에 포함된 턴 수
```

### 2. 현재 데이터 상태

```sql
SELECT
    COUNT(*) FILTER (WHERE user_id IS NOT NULL) as with_user_id,
    COUNT(*) FILTER (WHERE user_id IS NULL) as without_user_id,
    COUNT(*) as total
FROM statedb.sessions;

-- 결과:
with_user_id: 0
without_user_id: 32
total: 32
```

**모든 세션이 user_id 없이 생성됨!** ❌

## 🔍 문제점 상세 분석

### 문제 1: 세션에 user_id가 저장 안 됨 ⚠️

**현상**:
- 32개 세션 모두 `user_id = NULL`
- `user_name`만 저장됨 (예: "품질테스트1", "최종테스트2")
- 인증된 사용자와 세션이 연결되지 않음

**원인**:
```python
# api_server.py의 /api/chat 엔드포인트
@app.post("/api/chat")
async def chat(request: ChatRequest):
    # user_id를 전달하지 않음!
    response = await execute_graph(
        scenario_id=request.scenario_id,
        user_input=request.user_input,
        user_name=request.user_name,     # user_name만 전달
        session_id=request.session_id
        # user_id=??? (누락!)
    )
```

**영향**:
- 사용자별 세션 조회 불가능
- 사용자별 대화 히스토리 추적 불가능
- **사용자별 장기기억 구축 불가능** ❌

### 문제 2: 세션별 요약 vs 유저별 요약 ⚠️

**현재 구조**:
```
sessions 테이블
├── session_id: UUID (세션 단위)
├── user_id: UUID (NULL)
└── conversation_summary: TEXT (세션별 요약)

문제: 한 사용자가 여러 세션을 가질 경우?
User A
 ├── Session 1: summary 1
 ├── Session 2: summary 2
 └── Session 3: summary 3

→ 어떻게 User A의 전체 장기기억을 관리?
```

**시나리오 예시**:
```
사용자 "김태민" (user_id: abc-123)

세션 1 (어제):
- 대화: "렌고쿠를 좋아한다고 말함"
- 요약: "사용자는 렌고쿠를 선호"

세션 2 (오늘):
- 대화: "이노스케는 별로라고 말함"
- 요약: "사용자는 이노스케를 싫어함"

문제: 세션 2에서 세션 1의 정보를 어떻게 기억?
→ user_id로 이전 세션들의 요약을 가져와야 함!
```

### 문제 3: 장기기억 조회 불가능 ⚠️

**의도된 사용 방식**:
```python
# LLM에게 제공할 컨텍스트
def get_user_memory(user_id: str) -> str:
    """사용자의 장기기억 가져오기"""

    # 의도: 해당 사용자의 모든 세션 요약을 통합
    sessions = db.get_user_sessions(user_id)
    summaries = [s.conversation_summary for s in sessions]

    return "\n".join(summaries)
```

**현재 상황**:
```python
def get_user_memory(user_id: str) -> str:
    # user_id가 모두 NULL이라 조회 불가능!
    sessions = db.get_user_sessions(user_id)  # 결과: []

    return ""  # 빈 문자열 반환
```

## 🎯 해결 방안

### 방안 1: 현재 구조 활용 (세션별 요약 + user_id 연결) ⭐

**장점**:
- 마이그레이션 불필요
- 기존 테이블 구조 그대로 사용

**단점**:
- 여러 세션의 요약을 매번 조합해야 함
- 요약이 너무 길어질 수 있음

**구현 방안**:

#### 1-1. API 서버 수정 (세션 생성 시 user_id 포함)
```python
# api_server.py
@app.post("/api/chat")
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user_optional)  # JWT 인증
):
    # user_id 추출
    user_id = current_user.get('user_id') if current_user else None

    # 세션 생성/조회 시 user_id 포함
    session = SESSION_MANAGER.get_or_create_session(
        session_id=request.session_id,
        scenario_id=request.scenario_id,
        user_name=request.user_name,
        user_id=user_id  # 추가!
    )
```

#### 1-2. SessionManager 수정
```python
# session_manager.py
def create_new_session(
    self,
    session_id: str,
    scenario_id: str,
    user_name: str = None,
    user_id: str = None  # 추가!
):
    """세션 생성 시 user_id 포함"""
    self.db_manager.create_session(
        session_id=session_id,
        scenario_id=scenario_id,
        user_name=user_name,
        user_id=user_id  # DB에 저장
    )
```

#### 1-3. 유저별 장기기억 조회
```python
# memory_manager.py (새로 작성)
class UserMemoryManager:
    def get_user_long_term_memory(self, user_id: str, limit: int = 5) -> str:
        """사용자의 최근 N개 세션 요약을 통합"""

        # 최근 세션들 조회 (user_id로 필터링)
        sessions = self.db_manager.get_user_recent_sessions(
            user_id=user_id,
            limit=limit
        )

        # 요약들을 시간순으로 결합
        summaries = []
        for session in sessions:
            if session.conversation_summary:
                summaries.append(
                    f"[{session.created_at}] {session.conversation_summary}"
                )

        return "\n\n".join(summaries)
```

#### 1-4. LLM 프롬프트에 포함
```python
# children_agent.py
async def generate_response(self, state: GraphState):
    # 유저 장기기억 가져오기
    if state.get('user_id'):
        user_memory = memory_manager.get_user_long_term_memory(
            user_id=state['user_id'],
            limit=3  # 최근 3개 세션의 요약
        )

        # 프롬프트에 추가
        prompt = f"""
        [이전 대화 기억]
        {user_memory}

        [현재 대화]
        {current_conversation}

        위 정보를 바탕으로 응답을 생성하세요.
        """
```

### 방안 2: 별도 User Memory 테이블 생성 (권장) ⭐⭐⭐

**장점**:
- 유저별 장기기억 명확하게 관리
- 세션과 독립적으로 업데이트 가능
- 요약 압축 및 정리 용이

**단점**:
- 새로운 마이그레이션 필요
- 추가 테이블 관리 필요

**구현 방안**:

#### 2-1. 새 테이블 설계
```sql
-- 006_user_long_term_memory.sql
CREATE TABLE IF NOT EXISTS statedb.user_memories (
    memory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES statedb.users(user_id) ON DELETE CASCADE,
    memory_type VARCHAR(50) NOT NULL,  -- 'character_preference', 'story_progress', 'conversation_style' 등
    memory_key VARCHAR(255),            -- 'favorite_character', 'disliked_character' 등
    memory_value TEXT NOT NULL,         -- 실제 기억 내용
    confidence REAL DEFAULT 1.0,        -- 신뢰도 (0.0-1.0)
    source_session_id UUID REFERENCES statedb.sessions(session_id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP                -- 기억 만료 시간 (선택)
);

CREATE INDEX idx_user_memories_user ON statedb.user_memories(user_id, memory_type);
CREATE INDEX idx_user_memories_key ON statedb.user_memories(memory_key);
CREATE INDEX idx_user_memories_updated ON statedb.user_memories(updated_at DESC);

COMMENT ON TABLE statedb.user_memories IS '사용자별 장기 기억 (세션 독립적)';
COMMENT ON COLUMN statedb.user_memories.memory_type IS '기억 유형 (선호, 스토리 진행도 등)';
COMMENT ON COLUMN statedb.user_memories.confidence IS '기억의 신뢰도 (반복 확인 시 증가)';
```

#### 2-2. 기억 저장 예시
```python
# memory_manager.py
class UserMemoryManager:
    def save_memory(
        self,
        user_id: str,
        memory_type: str,
        memory_key: str,
        memory_value: str,
        source_session_id: str = None,
        confidence: float = 1.0
    ):
        """사용자 기억 저장"""
        self.db_manager.upsert_user_memory(
            user_id=user_id,
            memory_type=memory_type,
            memory_key=memory_key,
            memory_value=memory_value,
            source_session_id=source_session_id,
            confidence=confidence
        )

    def get_user_memories(
        self,
        user_id: str,
        memory_type: str = None,
        min_confidence: float = 0.5
    ) -> List[UserMemory]:
        """사용자 기억 조회"""
        return self.db_manager.get_user_memories(
            user_id=user_id,
            memory_type=memory_type,
            min_confidence=min_confidence
        )
```

#### 2-3. 실제 사용 예시
```python
# 대화 후 기억 추출 및 저장
async def extract_and_save_memories(
    user_id: str,
    session_id: str,
    dialogues: List[Dialogue]
):
    """대화에서 중요한 정보를 추출하여 장기기억으로 저장"""

    # LLM을 사용하여 기억할 만한 정보 추출
    extraction_prompt = f"""
    다음 대화에서 사용자에 대해 기억해야 할 정보를 추출하세요:
    {dialogues}

    JSON 형식으로 반환:
    [
        {{"type": "character_preference", "key": "favorite", "value": "렌고쿠"}},
        {{"type": "personality", "key": "communication_style", "value": "직설적"}}
    ]
    """

    memories = await llm.extract_memories(extraction_prompt)

    # DB에 저장
    for memory in memories:
        memory_manager.save_memory(
            user_id=user_id,
            memory_type=memory['type'],
            memory_key=memory['key'],
            memory_value=memory['value'],
            source_session_id=session_id
        )
```

#### 2-4. 기억 조회 및 활용
```python
# children_agent.py
async def generate_response(self, state: GraphState):
    user_id = state.get('user_id')

    if user_id:
        # 캐릭터 선호도 기억 조회
        character_prefs = memory_manager.get_user_memories(
            user_id=user_id,
            memory_type='character_preference'
        )

        # 대화 스타일 기억 조회
        comm_style = memory_manager.get_user_memories(
            user_id=user_id,
            memory_type='communication_style'
        )

        # 프롬프트에 포함
        memory_context = f"""
        [사용자 정보]
        - 선호 캐릭터: {character_prefs[0].memory_value if character_prefs else '알 수 없음'}
        - 대화 스타일: {comm_style[0].memory_value if comm_style else '일반적'}
        """

        # LLM 호출 시 포함
        response = await llm.generate(prompt + memory_context)
```

### 방안 3: 하이브리드 접근 (최적) ⭐⭐⭐⭐

**개념**:
- 세션별 요약 (sessions.conversation_summary): 단기 기억
- 유저별 장기기억 (user_memories): 장기 기억

**구조**:
```
User (user_id)
├── sessions (여러 개)
│   ├── session 1: conversation_summary (최근 10턴 요약)
│   ├── session 2: conversation_summary (최근 10턴 요약)
│   └── session 3: conversation_summary (최근 10턴 요약)
└── user_memories (통합 장기기억)
    ├── memory 1: "렌고쿠를 선호함" (confidence: 0.95)
    ├── memory 2: "이노스케를 싫어함" (confidence: 0.85)
    └── memory 3: "직설적인 대화 선호" (confidence: 0.7)
```

**LLM 프롬프트 구성**:
```python
async def build_context(user_id: str, session_id: str):
    # 1. 현재 세션의 최근 요약 (단기)
    current_summary = get_session_summary(session_id)

    # 2. 사용자 장기기억 (장기)
    long_term_memories = memory_manager.get_user_memories(user_id)

    # 3. 이전 세션 요약 (중기) - 선택적
    recent_sessions = get_recent_session_summaries(user_id, limit=2)

    return f"""
    [장기 기억 - 사용자 특성]
    {format_memories(long_term_memories)}

    [중기 기억 - 최근 대화 요약]
    {format_summaries(recent_sessions)}

    [단기 기억 - 현재 세션]
    {current_summary}
    """
```

## 📋 구현 우선순위

### 1단계: 긴급 (즉시 수행) 🔴
- [ ] API 서버 수정: 세션 생성 시 user_id 포함
- [ ] SessionManager 수정: user_id 저장 로직 추가
- [ ] 기존 세션 user_id 업데이트 (가능한 경우)

### 2단계: 단기 (1-2일) 🟡
- [ ] user_memories 테이블 마이그레이션 작성
- [ ] UserMemoryManager 클래스 구현
- [ ] 기억 추출 로직 구현 (LLM 활용)

### 3단계: 중기 (1주일) 🟢
- [ ] 기억 업데이트 로직 (신뢰도 조정)
- [ ] 기억 만료 및 정리 시스템
- [ ] 기억 기반 개인화 응답 구현

## 💡 즉시 적용 가능한 임시 방안

**user_name을 user_id 대신 사용**:
```python
# 현재 32개 세션은 user_name만 있음
# 임시로 user_name을 키로 사용 가능 (완벽하지 않음)

def get_user_memory_by_name(user_name: str) -> str:
    """user_name으로 이전 세션들 조회 (임시)"""
    sessions = db.query(
        "SELECT conversation_summary FROM statedb.sessions "
        "WHERE user_name = %s "
        "ORDER BY created_at DESC LIMIT 3",
        (user_name,)
    )

    return "\n".join([s['conversation_summary'] for s in sessions])
```

**한계**:
- user_name은 중복 가능 (고유하지 않음)
- 인증된 사용자와 연결 안 됨
- 임시 방편일 뿐, 근본적 해결 아님

## 📊 영향도 분석

| 구성요소 | 현재 상태 | 문제 심각도 | 개선 후 |
|----------|-----------|-------------|---------|
| 세션 생성 | user_id 없음 | 🔴 심각 | ✅ user_id 포함 |
| 장기기억 조회 | 불가능 | 🔴 심각 | ✅ 유저별 조회 가능 |
| 개인화 응답 | 불가능 | 🟡 중간 | ✅ 사용자 맞춤 응답 |
| 데이터 분석 | 제한적 | 🟡 중간 | ✅ 유저별 분석 가능 |

## 🎯 결론

### 현재 문제
1. ❌ **세션에 user_id가 저장 안 됨** - 모든 세션이 익명
2. ❌ **유저별 장기기억 불가능** - 세션별 요약만 가능
3. ❌ **개인화 경험 제공 불가** - 사용자 특성 기억 못함

### 해결책
**권장: 방안 3 (하이브리드)**
1. ✅ API 서버 수정 (user_id 저장)
2. ✅ user_memories 테이블 생성
3. ✅ 단기/중기/장기 기억 통합 관리

### 배포 전 필수 작업
- **user_id 연동**: API 서버 + SessionManager 수정
- **기억 시스템 설계**: 어떤 정보를 장기기억으로 저장할지 정의

---

**작성자**: Claude Code
**최종 업데이트**: 2025-10-30 오후 10시 15분
**다음 문서**: [19_session_user_integration_implementation.md] (작성 예정)
