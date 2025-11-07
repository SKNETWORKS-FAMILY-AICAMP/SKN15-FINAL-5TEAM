"""
백엔드 전역에서 공유하는 상수 모음.
"""

# 시나리오 인트로 스테이지 식별자
INTRO_STAGE_TAG = "INTRO"
INTRO_STAGE_TAGS = ("INTRO", "상현_삼_등장")

# 반복 입력 제어
DEFAULT_LOOP_LIMIT = 3
URGENT_LOOP_LIMIT = 2
SYSTEM_MESSAGE_LOOP_EXCEEDED = "[꺾쇠 까마귀]⚠️ 동일한 발화가 반복되어 자동 진행합니다."

# 오프토픽 허용 기본 횟수
FALLBACK_ALLOW_NORMAL = 3
