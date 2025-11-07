"""
Configuration Loader

프롬프트 및 설정을 로드하는 유틸리티
TODO: 실제 YAML/JSON 기반 구현 필요
"""

from typing import Dict, Any
import logging

log = logging.getLogger(__name__)


class ConfigLoader:
    """설정 로더 (스텁 구현)"""

    def __init__(self):
        """초기화"""
        self._prompts = self._load_default_prompts()

    def _load_default_prompts(self) -> Dict[str, Any]:
        """기본 프롬프트 반환 (스텁)"""
        # TODO: 실제 YAML/JSON 파일에서 로드
        return {
            "llm_prompts": {
                "fallback": {
                    "off_topic_base": "사용자가 게임과 무관한 대화를 시도했습니다.",
                    "off_topic_user": "지금은 게임에 집중해주세요.",
                    "urgent_off_topic_base": "사용자가 긴급한 상황에서 게임과 무관한 대화를 시도했습니다.",
                    "urgent_off_topic_user": "지금은 중요한 시점입니다. 게임에 집중해주세요."
                },
                "mission": {
                    "system": "당신은 미션 진행을 돕는 AI입니다.",
                    "user": "다음 미션을 진행해주세요.",
                    "recruitment_judge": "사용자의 입력이 미션 목표를 달성했는지 판단해주세요.",
                    "recruitment_judge_user": "사용자 입력: {user_input}\n미션 목표: {mission_goal}"
                },
                "router": {
                    "system": "당신은 대화 흐름을 라우팅하는 AI입니다.",
                    "user": "사용자 입력을 분석해주세요.",
                    "topic_classifier": "사용자 입력의 토픽을 분류해주세요.",
                    "topic_classifier_user": "사용자 입력: {user_input}"
                },
                "dialogue": {
                    "system": "당신은 캐릭터와의 대화를 생성하는 AI입니다.",
                    "user": "자연스러운 대화를 생성해주세요.",
                    "validation": "생성된 대화가 적절한지 검증해주세요.",
                    "correction_template": "다음 문제를 수정해주세요: {issue}"
                },
                "children": {
                    "system": "당신은 동화책 스타일의 이야기를 생성하는 AI입니다.",
                    "user": "동화 형식으로 이야기를 생성해주세요.",
                    "dialogue_generation": "아이들을 위한 대화를 생성해주세요."
                },
                "llm_beats": {
                    "system": "당신은 스토리 비트를 생성하는 AI입니다.",
                    "user": "다음 스토리 비트를 생성해주세요."
                }
            }
        }

    def get_prompts(self) -> Dict[str, Any]:
        """프롬프트 딕셔너리 반환"""
        return self._prompts


# 싱글톤 인스턴스
_config_loader_instance = None


def get_config_loader() -> ConfigLoader:
    """ConfigLoader 싱글톤 인스턴스 반환"""
    global _config_loader_instance
    if _config_loader_instance is None:
        _config_loader_instance = ConfigLoader()
        log.debug("ConfigLoader initialized")
    return _config_loader_instance
