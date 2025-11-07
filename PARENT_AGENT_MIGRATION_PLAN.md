# Parent Agent 마이그레이션 계획

## 현재 상황 분석

### 기존 src/ 구조
```
src/
├── domain/
│   ├── agents/          # ParentAgent, GuardrailAgent, RouterAgent 등
│   ├── handlers/        # MissionHandler, SceneHandler 등
│   ├── services/        # 158개 Python 파일
│   │   ├── orchestration/   # state_tools, scene_tools, scenario_loader
│   │   ├── generation/      # children_agent, fallback_llm
│   │   ├── classification/  # intent_detector, entity_extractor
│   │   ├── evaluation/      # affinity_calculator, memory_extractor
│   │   └── validation/      # spell_checker
│   └── models/          # 데이터 모델들
├── core/
│   ├── utils/           # llm_client, logger
│   └── config/          # config_loader
└── infrastructure/      # DB, Redis 등
```

### 의존성 문제
1. **복잡한 Import 체인**
   - ParentAgent → Handlers → Services → Core Utils
   - 순환 참조 가능성
   - 158개 파일의 복잡한 의존성

2. **누락된 패키지**
   - `pydantic_settings` 등 일부 의존성 누락
   - 직접 import 시도 시 ModuleNotFoundError 발생

3. **설정 시스템 차이**
   - 기존: `src.core.config.config_loader` (YAML 기반)
   - 신규: `app.core.config` (Pydantic Settings 기반)

## 마이그레이션 전략

### 옵션 1: 점진적 마이그레이션 (권장)
**단계별 접근으로 안정성 확보**

#### Phase 1: 핵심 서비스만 먼저 마이그레이션
1. **ChildrenAgent 마이그레이션**
   - LLM 대사 생성 로직
   - 의존성: LLMClient, tone_profile_loader
   - 목표: `app/features/chat/services/llm_service.py`

2. **간단한 Guardrail/Router**
   - 입력 검증, 토픽 분류
   - 목표: `app/features/chat/services/guardrail_service.py`

3. **State Management**
   - state_tools, scene_tools 단순화
   - 목표: `app/features/chat/services/state_service.py`

#### Phase 2: Handler 통합
1. **Handler 패턴 단순화**
   - 기존: MissionHandler, SceneHandler, NarrativeHandler 등 5개
   - 신규: 통합된 StageHandler 하나로 단순화
   - 목표: `app/features/chat/agent/stage_handler.py`

#### Phase 3: Parent Agent 완성
1. **Parent Agent 실제 구현**
   - Phase 1, 2의 서비스 활용
   - 스테이지 라우팅 로직
   - 목표: `app/features/chat/agent/parent.py` 업데이트

### 옵션 2: 하이브리드 접근 (임시)
**필요한 부분만 src/에서 import**

```python
# app/features/chat/agent/parent.py
try:
    from src.domain.agents.parent_agent import ParentAgent as LegacyParent
    LEGACY_AVAILABLE = True
except ImportError:
    LEGACY_AVAILABLE = False

class ChatParent:
    def __init__(self):
        self.legacy = LegacyParent() if LEGACY_AVAILABLE else None

    async def execute(...):
        if self.legacy:
            # Legacy 코드 사용
            return await self._execute_legacy(...)
        else:
            # Dummy 응답
            return self._dummy_response(...)
```

**문제점:**
- src/ 의존성 전체를 유지해야 함
- 두 시스템 병행 유지의 복잡도
- 향후 정리 어려움

### 옵션 3: 완전 재작성 (장기)
**새로운 아키텍처로 처음부터 구현**

**장점:**
- 깨끗한 설계
- 4-Layer 아키텍처 완전 준수
- 불필요한 레거시 코드 제거

**단점:**
- 시간 소요 큼
- 기존 로직 재현 필요
- 테스트 부담

## 권장 실행 계획

### 🎯 Phase 1: LLM Service 마이그레이션 (우선)

#### 1.1 LLMClient 재구현
```
app/core/llm/
├── __init__.py
├── client.py          # LLMClient 재구현 (OpenAI/Anthropic)
└── prompts.py         # 프롬프트 템플릿 관리
```

#### 1.2 ChildrenAgent → LLMService
```
app/features/chat/services/
├── __init__.py
└── llm_service.py     # 대사 생성 로직
```

**마이그레이션 범위:**
- `src/domain/services/generation/children_agent.py` 로직
- Beat 기반 대사 생성
- LLM 응답 정규화

#### 1.3 통합 테스트
- 더미 시나리오로 대사 생성 테스트
- Frontend 연동 확인

### 🎯 Phase 2: State & Stage Management

#### 2.1 State Service
```
app/features/chat/services/
├── state_service.py   # 세션 상태 관리
└── stage_service.py   # 스테이지 진행 관리
```

#### 2.2 Stage Handler 통합
```
app/features/chat/agent/
└── stage_handler.py   # 통합 스테이지 처리
```

### 🎯 Phase 3: Parent Agent 완성

```python
# app/features/chat/agent/parent.py

from ..services.llm_service import LLMService
from ..services.state_service import StateService
from ..services.stage_service import StageService
from .stage_handler import StageHandler

class ChatParent:
    def __init__(self):
        self.llm = LLMService()
        self.state = StateService()
        self.stage = StageService()
        self.handler = StageHandler()

    async def execute(self, user_message, session_state, scenario_id):
        # 1. State 준비
        state = await self.state.prepare(session_state, scenario_id)

        # 2. Stage 결정
        current_stage = await self.stage.resolve(state)

        # 3. Handler 실행
        result = await self.handler.handle(current_stage, state, user_message)

        # 4. LLM 대사 생성
        dialogues = await self.llm.generate_dialogues(result.beats, state)

        # 5. State 업데이트
        updated_state = await self.state.update(state, result)

        return DialogueResult(
            dialogues=dialogues,
            next_stage=result.next_stage,
            stage_complete=result.stage_complete,
            updated_state=updated_state,
            affinity_delta=result.affinity_delta
        )
```

## 다음 즉시 실행할 작업

1. **LLMClient 재구현** (`app/core/llm/client.py`)
   - OpenAI API 호출
   - 에러 핸들링
   - 프롬프트 템플릿 시스템

2. **간단한 대사 생성 테스트**
   - 하드코딩된 시나리오로 테스트
   - Frontend 연동 확인

3. **점진적 확장**
   - State 관리 추가
   - Stage 라우팅 추가
   - Handler 로직 추가

## 파일 정리 계획

### 단계별 정리
1. **Phase 1 완료 후**: src/domain/services/generation/ 일부 제거
2. **Phase 2 완료 후**: src/domain/handlers/ 제거
3. **Phase 3 완료 후**: src/domain/agents/ 제거
4. **최종**: src/ 전체 제거 또는 참고용 보관

## 타임라인 예상

- **Phase 1 (LLM Service)**: 2-3시간
- **Phase 2 (State/Stage)**: 3-4시간
- **Phase 3 (Parent 완성)**: 2-3시간
- **테스트 & 버그 수정**: 2-3시간

**총 예상 시간**: 9-13시간 (1-2일)

## 결론

**권장 접근**: 옵션 1 (점진적 마이그레이션)
- Phase 1부터 시작하여 단계별 검증
- 각 단계마다 Git 커밋
- Frontend-Backend 연동 지속 확인

---

## 진행 현황

### ✅ Phase 1: LLM Service 마이그레이션 (완료)
**완료 일시**: 2025-11-08

**구현 내용:**
1. ✅ LLMClient 재구현 (`app/core/llm/client.py`)
   - OpenAI API 통합 (gpt-4o-mini)
   - Rate Limiting (60 requests/minute)
   - Response Caching
   - JSON mode 지원

2. ✅ PromptTemplate 시스템 (`app/core/llm/prompts.py`)
   - Template 기반 프롬프트 관리
   - DialoguePrompts: SIMPLE_DIALOGUE, BEAT_DIALOGUE

3. ✅ LLMService 구현 (`app/features/chat/services/llm_service.py`)
   - generate_simple_dialogue: 단순 대화 생성
   - generate_beat_dialogue: Beat 기반 대화 생성 (미통합)
   - _normalize_llm_response: 다양한 LLM 응답 형식 지원

4. ✅ Parent Agent 연동
   - LLMService를 통한 실제 대사 생성
   - Fallback 에러 처리

**커밋**: `feat: Phase 1 - LLM Service integration complete`

---

### ✅ Phase 2: State & Stage Management (완료)
**완료 일시**: 2025-11-08

**구현 내용:**
1. ✅ StateService 구현 (`app/features/chat/services/state_service.py`)
   - prepare_state: 세션 상태 초기화 및 검증
   - update_state: 상태 업데이트 (턴 카운트, 대화 이력)
   - reset_stage: 스테이지 전환
   - get_progress_stats: 진행도 통계

2. ✅ StageService 구현 (`app/features/chat/services/stage_service.py`)
   - StageDefinition: 스테이지 정의 클래스
   - resolve_stage: 현재 스테이지 결정
   - check_stage_complete: 스테이지 완료 확인 (3턴 기준)
   - get_next_stage: 다음 스테이지 결정
   - 기본 스테이지: intro, main

3. ✅ Parent Agent 통합
   - StateService + StageService 연동
   - 자동 스테이지 전환 로직 (intro → main after 3 turns)
   - 대화 이력 관리 (최근 20개 유지)

**커밋**: `feat: Phase 2 - State & Stage Management integration`

---

### ✅ Phase 3: Guardrail & Router Agents (완료)
**완료 일시**: 2025-11-08

**구현 내용:**
1. ✅ GuardrailAgent 구현 (`app/features/chat/agent/guards/guardrail.py`)
   - 입력 검증 (길이: 1-500자)
   - 시스템 명령어 차단 (regex 기반)
   - 금지 키워드 검사 (self_harm, sexual, violence, hate, system)
   - 경고 시스템 (2회 경고 → 차단)
   - 무의미 입력 필터링 (반복 문자, 특수문자만)

2. ✅ RouterAgent 구현 (`app/features/chat/agent/guards/router.py`)
   - 토픽 분류 (keyword 기반)
   - 지원 토픽: greeting, farewell, question, emotion_positive, emotion_negative,
     agreement, disagreement, personal, scenario_specific, general
   - 컨텍스트 기반 우선순위 조정 (턴 수, 스테이지 상태)
   - 신뢰도 계산 (confidence score)
   - 응답 전략 제공 (emotion, style, max_turns 등)

3. ✅ Parent Agent 최종 통합
   - 파이프라인 순서:
     1. State 준비
     2. **Guardrail: 입력 검증** (NEW)
     3. **Router: 토픽 분류** (NEW)
     4. Stage 결정
     5. LLM 대사 생성 (Router 전략 반영)
     6. Stage 완료 확인
     7. 다음 Stage 결정
     8. State 업데이트
     9. Result 생성
   - 검증 실패 시 즉시 에러 메시지 반환
   - Router 전략에 따른 감정(emotion) 자동 설정

**커밋**: (진행 중)

---

### 🔄 Next Steps (향후 계획)

#### Phase 4: Beat 기반 대화 생성 (선택)
- generate_beat_dialogue 메서드 활성화
- Beat 정의 및 관리
- StageService beats 연동

#### Phase 5: 임베딩 기반 고도화 (선택)
- Guardrail: 키워드 → 임베딩 기반 검증
- Router: 키워드 → 임베딩 기반 분류
- 의미 기반 유사도 계산

#### Phase 6: Scenario System (필수)
- YAML 시나리오 로더
- DB에서 시나리오 로드
- 캐릭터 설정 동적 로드

---

## 기술 스택 정리

### Phase 1-3에서 사용된 기술
- **LLM**: OpenAI GPT-4o-mini
- **Rate Limiting**: Custom RateLimiter 구현
- **Caching**: In-memory dict cache
- **Prompt Management**: string.Template 기반
- **Validation**: Regex + keyword matching
- **Topic Classification**: Keyword-based scoring
- **State Management**: Dict-based session state
- **Stage Management**: Hardcoded stage definitions

### 향후 추가 예정
- **Embedding**: OpenAI embeddings or sentence-transformers
- **Vector DB**: Pinecone or FAISS (유사도 검색)
- **Scenario Storage**: PostgreSQL + YAML files
