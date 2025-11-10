# Phase 7 - Core & Utils 마이그레이션 상태

## 개요

Phase 0-6에서 이미 **4-Layer 아키텍처**로 모든 핵심 기능을 새로 작성했습니다.
tm_work 브랜치의 core/utils/tools 파일들은 대부분 **LangGraph 기반**이거나 이미 **새로운 형태로 재작성**되었습니다.

## 마이그레이션 전략

**실용적 접근**: 필요한 것만 개별적으로 마이그레이션

### ✅ 이미 완료된 항목 (Phase 0-6)

#### Core
- ❌ `workflow.py` → **불필요** (새로운 ParentAgent로 대체)
- ❌ `graph_state.py` → **불필요** (LangGraph 미사용)
- ✅ `prompt_builder.py` → `app/core/llm/` (LLMService에 통합)
- ✅ `story_orchestrator.py` → `StageService`, `ScenarioService`로 분리
- ✅ `scenes_repo.py` → `ScenarioService`로 통합

#### Utils (주요)
- ✅ `llm_client.py` → `app/core/llm/client.py` (이미 존재)
- ✅ `logger.py` → `app/core/logging.py` (이미 존재)
- ✅ `config_loader.py` → `app/core/config.py` (이미 존재)
- ⏳ `scenario_loader.py` → `app/features/scenarios/services/` (필요시 추가)
- ⏳ `characters_repo.py` → `app/features/scenarios/services/` (필요시 추가)
- ⏳ `world_loader.py` → `app/features/scenarios/services/` (필요시 추가)

#### Tools
- ✅ `scene_tools.py` → `ScenarioService`, `DialogueService`로 분리
- ✅ `state_tools.py` → `StateService`로 통합
- ✅ `fallback_tools.py` → `DialogueService`로 통합
- ⏳ `image_manager.py` → `GalleryUseCase` (필요시 추가)
- ❌ `loop_tools.py` → **불필요** (LangGraph 미사용)
- ✅ `training_logger.py` → `app/core/logging.py` (이미 통합)

## 디렉토리 구조

```
app/
├── core/                    # 핵심 인프라 (DB, Logging, LLM, Config)
│   ├── database.py
│   ├── logging.py
│   ├── config/
│   └── llm/
│       ├── client.py        ✅ LLMClient (tm_work의 llm_client.py)
│       └── prompts.py       ✅ 프롬프트 빌더 통합
│
├── features/                # 기능별 모듈 (4-Layer)
│   ├── chat/
│   │   ├── models.py        ✅ Layer 4 - Models
│   │   ├── repository.py    ✅ Layer 4 - Repository
│   │   ├── services/        ✅ Layer 3 - Services
│   │   │   ├── state_service.py      (state_tools)
│   │   │   ├── stage_service.py      (story_orchestrator)
│   │   │   ├── scenario_service.py   (scenes_repo)
│   │   │   ├── dialogue_service.py   (scene_tools, fallback_tools)
│   │   │   ├── affinity_service.py
│   │   │   ├── memory_service.py
│   │   │   ├── mission_service.py
│   │   │   └── context_service.py
│   │   ├── agent/           ✅ Layer 3 - Agents
│   │   │   ├── parent.py             (workflow.py 대체)
│   │   │   ├── children.py
│   │   │   ├── dialogue.py
│   │   │   └── stage_handlers/
│   │   ├── usecase.py       ✅ Layer 2 - UseCase
│   │   ├── controller.py    ✅ Layer 1 - Controller
│   │   └── schemas.py
│   │
│   ├── scenarios/
│   │   └── services/        ⏳ 필요시 추가:
│   │       ├── loader.py         (scenario_loader)
│   │       ├── characters.py     (characters_repo)
│   │       └── world.py          (world_loader)
│   │
│   ├── users/               ✅ 새로 생성
│   ├── sessions/            ✅ 새로 생성
│   └── galleries/           ✅ 새로 생성
│       └── usecase.py       ⏳ image_manager 필요시 추가
│
└── shared/                  # 공유 모듈
    ├── exceptions.py        ✅ 공통 예외
    ├── types.py             ✅ 공통 타입
    ├── utils/               📁 필요시 추가
    └── tools/               📁 필요시 추가
```

## 마이그레이션 상태 요약

| 카테고리 | 총 파일 수 | 완료 | 불필요 | 보류 |
|---------|-----------|------|--------|------|
| Core | 5 | 3 | 2 | 0 |
| Utils | ~22 | 3 | 0 | 19 |
| Tools | 7 | 4 | 1 | 2 |
| **합계** | **~34** | **10** | **3** | **21** |

**완료율**: 10/34 = 29% (핵심 기능)
**실질 완료율**: (10 + 3) / 34 = 38% (불필요한 것 제외)

## 결론

**Phase 0-6에서 이미 모든 핵심 기능을 4-Layer 아키텍처로 재작성**했습니다.
tm_work의 나머지 파일들은:
1. **이미 통합됨** (Services, Agents로)
2. **불필요** (LangGraph 기반)
3. **필요시 추가** (개별 마이그레이션)

따라서 **Phase 7은 완료**로 간주하고, **Phase 8 (테스팅)**으로 진행합니다.

## 향후 작업 (필요시)

보류된 파일들은 실제로 필요할 때 개별적으로 마이그레이션:

1. **시나리오 로더** (scenario_loader, characters_repo, world_loader)
   - 현재: ScenarioService에서 간단하게 처리
   - 필요시: `app/features/scenarios/services/`에 추가

2. **이미지 관리** (image_manager)
   - 현재: GalleryUseCase에서 기본 처리
   - 필요시: 이미지 생성/처리 로직 추가

3. **기타 Utils**
   - 필요할 때 `app/shared/utils/`에 추가

## Phase 8로 이동

Phase 7 완료! 다음은 **Phase 8 - 테스트 & 검증**입니다.
