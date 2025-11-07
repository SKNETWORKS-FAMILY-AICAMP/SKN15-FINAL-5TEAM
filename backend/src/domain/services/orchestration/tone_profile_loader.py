"""
Tone Profile Loader

캐릭터별 톤/분위기 프로파일을 로드하는 유틸리티
TODO: 실제 구현 필요
"""

from typing import Dict, Any, Optional
from src.core.utils.logger import log



def load_tone_profiles(
    character_refs: Dict[str, Any],
    scenario_key: Optional[str] = None
) -> Dict[str, Dict[str, Any]]:
    """
    캐릭터 톤 프로파일 로드 (스텁 구현)

    Args:
        character_refs: 캐릭터 참조 딕셔너리
        scenario_key: 시나리오 키 (선택적)

    Returns:
        캐릭터별 톤 프로파일 딕셔너리
    """
    # TODO: 실제 구현 필요 - 현재는 빈 딕셔너리 반환
    log.debug(f"load_tone_profiles called with character_refs={list(character_refs.keys())}, scenario_key={scenario_key}")
    return {}


def compose_llm_prompt(
    stage_tag: str,
    beats: list,
    tone_profiles: Dict[str, Any],
    speaker_pool: list,
    context_summary: Optional[str] = None,
    stage_turn: int = 0,
    stage_type: str = "",
    stage_objective: Optional[str] = None,
    intent_options: Optional[Dict] = None,
    latest_user_input: Optional[str] = None,
    recent_dialogues: Optional[list] = None,
    conversation_summary: Optional[str] = None,
) -> str:
    """
    LLM 프롬프트 생성 (스텁 구현)

    Args:
        stage_tag: 스테이지 태그
        beats: 비트 리스트
        tone_profiles: 톤 프로파일
        speaker_pool: 발화자 풀
        context_summary: 컨텍스트 요약
        stage_turn: 스테이지 턴
        stage_type: 스테이지 타입
        stage_objective: 스테이지 목표
        intent_options: 의도 옵션
        latest_user_input: 최신 사용자 입력
        recent_dialogues: 최근 대화
        conversation_summary: 대화 요약

    Returns:
        LLM 프롬프트 문자열
    """
    log.debug(f"compose_llm_prompt called for stage={stage_tag}, beats={len(beats)}, speakers={speaker_pool}")

    # 간단한 프롬프트 생성
    prompt_parts = []

    # 스테이지 정보
    prompt_parts.append(f"## 현재 스테이지: {stage_tag}")
    if stage_objective:
        prompt_parts.append(f"목표: {stage_objective}")

    # 컨텍스트
    if context_summary:
        prompt_parts.append(f"\n## 상황:\n{context_summary}")

    # 비트 정보
    if beats:
        prompt_parts.append("\n## 장면 비트:")
        for i, beat in enumerate(beats[:5]):  # 최대 5개
            if isinstance(beat, dict):
                text = beat.get("text") or beat.get("goal") or beat.get("description") or ""
                speaker = beat.get("speaker", "narr")
                prompt_parts.append(f"{i+1}. [{speaker}] {text}")

    # 사용자 입력
    if latest_user_input:
        prompt_parts.append(f"\n## 사용자 입력:\n{latest_user_input}")

    # 최근 대화
    if recent_dialogues and len(recent_dialogues) > 0:
        prompt_parts.append("\n## 최근 대화:")
        for dialogue in recent_dialogues[-3:]:  # 최근 3개
            prompt_parts.append(f"- {dialogue}")

    # 발화자 정보
    prompt_parts.append(f"\n## 발화 가능한 캐릭터: {', '.join(speaker_pool)}")

    # 지시사항
    prompt_parts.append("\n## 지시사항:")
    prompt_parts.append("위 정보를 바탕으로 캐릭터들의 대사를 생성해주세요.")
    prompt_parts.append("각 대사는 캐릭터의 성격과 상황에 맞게 작성해주세요.")

    return "\n".join(prompt_parts)
