"""
조건부 엣지 함수들
"""
from ..graph_state import GraphState


def should_route(state: GraphState) -> str:
    """
    라우팅 필요 여부 결정

    Returns:
        "route" - RouterAgent로 이동
        "dialogue" - DialogueAgent로 이동
        "end" - 종료 (가드레일 실패)
    """
    # 가드레일 실패 시 종료
    if not state.get("is_safe", True):
        return "end"

    # router 타입 스테이지인 경우 라우팅
    if state.get("stage_type") == "router":
        return "route"

    # 그 외는 대화 생성
    return "dialogue"


def check_safety(state: GraphState) -> str:
    """
    출력 안전성 확인

    Returns:
        "safe" - 안전, 종료
        "unsafe" - 불안전, 재생성
    """
    if state.get("is_safe", True):
        return "safe"
    else:
        return "unsafe"
