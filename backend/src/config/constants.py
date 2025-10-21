"""
시스템 상수 정의 파일
모든 하드코딩된 값을 단일 출처에서 관리
"""

# ===== 턴 및 루프 제한 =====
DEFAULT_MAX_TURNS = 999
DEFAULT_STAGE_MAX_TURNS = 10
DEFAULT_LOOP_LIMIT = 3  # 반복 입력 한계 (일반 장면)
URGENT_LOOP_LIMIT = 1   # 반복 입력 한계 (급박한 장면)

# ===== Fallback 정책 =====
# 장면별 허용 횟수
FALLBACK_ALLOW_NORMAL = 3    # 일반 장면: 3회 허용 후 유도
FALLBACK_ALLOW_URGENT = 0    # 급박/전투 장면: 즉시 차단

# ===== Router 임계치 =====
ROUTER_ON_TOPIC_THRESHOLD = 0.7      # on_topic 판정 임계치
ROUTER_OFF_TOPIC_THRESHOLD = 0.3     # off_topic 판정 임계치

# ===== Guardrail 임계치 =====
GUARDRAIL_BLOCK_THRESHOLD = 0.9      # 즉시 차단 임계치
GUARDRAIL_WARNING_THRESHOLD = 0.6    # 경고 임계치

# ===== LLM 프로필 =====
LLM_MODEL_DEFAULT = "gpt-4o-mini"
LLM_MODEL_ADVANCED = "gpt-4o"
LLM_TEMPERATURE_DEFAULT = 0.7
LLM_TEMPERATURE_PRECISE = 0.3
LLM_MAX_TOKENS_DEFAULT = 500
LLM_MAX_TOKENS_EXTENDED = 1500

# ===== 캐릭터 시스템 =====
AFFINITY_MIN = 0
AFFINITY_MAX = 1000
AFFINITY_DEFAULT = 500
AFFINITY_INCREMENT_POSITIVE = 50
AFFINITY_INCREMENT_NEGATIVE = -30

# ===== 시나리오 기본값 =====
DEFAULT_SCENARIO_ID = "cutscene5_llm_driven"
SCENARIOS_PATH = "data/scenarios/"
CHARACTERS_PATH = "data/characters/"

# ===== 시스템 메시지 =====
SYSTEM_MESSAGE_BLOCKED = "⚠️  부적절한 입력이 감지되었습니다. 다시 입력해주세요."
SYSTEM_MESSAGE_OFF_TOPIC = "🤔 스토리와 관련 없는 내용인 것 같아요. 현재 상황에 맞는 선택을 해주세요."
SYSTEM_MESSAGE_LOOP_EXCEEDED = "⏰ 동일한 입력이 반복되고 있습니다. 스토리를 진행하겠습니다."

# ===== 재사용성 =====
SESSION_ISOLATION_ENABLED = True
REENTRY_PROTECTION_ENABLED = True

# ===== 로깅 =====
LOG_SANITIZED_ONLY = True
LOG_TELEMETRY_ENABLED = True
LOG_LEVEL = "INFO"

# ===== 금칙어 목록 (리소스 파일로 이동 권장) =====
# 불가피하게 코드에 포함할 경우 이곳에만 정의
BANNED_WORDS = [
    # 추후 data/resources/banned_words.json으로 이동 권장
]

# ===== 메타 명령어 =====
META_COMMANDS = ["save", "load", "help", "quit", "exit", "status"]

# ===== 디버그 =====
DEBUG_MODE = False
DEBUG_PRINT_STATE = False
DEBUG_PRINT_DECISIONS = False
