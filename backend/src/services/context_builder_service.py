"""
============================================================
🏗️ Context Builder Service — children_ctx 구성 로직
============================================================
ParentAgent의 children_ctx 구성 로직을 서비스로 분리합니다.
핸들러들이 생성한 기본 ctx에 공통 정보를 추가합니다.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.tools import scene_tools
from src.utils.logger import log


class ContextBuilderService:
    """
    Children Context 빌더 서비스

    ParentAgent가 핸들러 호출 후 수행하던 children_ctx 구성 로직을 분리했습니다.
    - character_refs, scenario_id 등 공통 정보 추가
    - context_summary, recent_dialogues 구성
    - prefetch_dialogues, fallback 처리
    - dynamic_speaker_stages 처리
    """

    @staticmethod
    def build_children_ctx(
        base_ctx: Dict[str, Any],
        state: Dict[str, Any],
        scenario: Dict[str, Any],
        stage: Optional[Dict[str, Any]] = None,
        next_stage: Optional[str] = None,
        immediate_advance: bool = False,
    ) -> Dict[str, Any]:
        """
        핸들러가 생성한 기본 ctx에 공통 정보를 추가하여 완전한 children_ctx를 구성합니다.

        Args:
            base_ctx: 핸들러가 생성한 기본 context
            state: 전체 state 객체
            scenario: 시나리오 정보
            stage: 현재 스테이지 정의
            next_stage: 다음 스테이지 태그 (있으면 적용)
            immediate_advance: 즉시 전환 여부

        Returns:
            완성된 children_ctx
        """
        children_ctx = dict(base_ctx)  # 사본 생성
        metadata = scenario.get("metadata") or {}

        # stage_tag 결정
        stage_tag = base_ctx.get("stage_tag") or (stage.get("tag") if stage else "unknown")
        if next_stage and immediate_advance:
            stage_tag = next_stage
            children_ctx["stage_tag"] = stage_tag

        # stage_type 결정
        if stage:
            if hasattr(scene_tools, "get_stage_type"):
                stage_type_value = scene_tools.get_stage_type(stage)
            else:
                stage_type_value = stage.get("type", "scene")
        else:
            stage_type_value = base_ctx.get("stage_type", "scene")

        if next_stage and immediate_advance:
            children_ctx["stage_type"] = stage_type_value
        else:
            children_ctx.setdefault("stage_type", stage_type_value)

        # Beats 및 speaker_pool 갱신
        if stage:
            if next_stage and immediate_advance:
                # 즉시 전환: 무조건 다음 스테이지 beats 사용
                children_ctx["beats"] = scene_tools.resolve_i18n_beats(stage, scenario)
                children_ctx["speaker_pool"] = stage.get("speaker_pool", [])
            else:
                # 대기 상태: 기존 beats 유지, 없으면 현재 스테이지 beats 사용
                if not children_ctx.get("beats") and not children_ctx.get("fallback"):
                    children_ctx["beats"] = scene_tools.resolve_i18n_beats(stage, scenario)
                if not children_ctx.get("speaker_pool"):
                    children_ctx["speaker_pool"] = stage.get("speaker_pool", [])

            # Stage objective
            objective = stage.get("objective")
            if objective:
                children_ctx["stage_objective"] = objective

            # Intent mapping
            intent_mapping = stage.get("intent_mapping")
            if intent_mapping:
                children_ctx["intent_options"] = intent_mapping
        else:
            children_ctx.setdefault("beats", [])
            children_ctx.setdefault("speaker_pool", [])

        # Context summary 및 최근 대화 추가
        children_ctx["context_summary"] = ContextBuilderService._build_context_summary(state)
        children_ctx["latest_user_input"] = state.get("user_input", "")
        children_ctx["recent_dialogues"] = ContextBuilderService._collect_recent_dialogues(state)

        # Dynamic speaker stages 처리 (allies_recruited 추가)
        stage_key = (stage.get("tag") if isinstance(stage, dict) else stage_tag) or ""
        stage_key_upper = stage_key.upper()
        dynamic_speaker_stages = {
            str(tag).upper()
            for tag in (metadata.get("dynamic_speaker_stages") or [])
            if isinstance(tag, str)
        }
        if stage_key_upper in dynamic_speaker_stages:
            recruits = state.get("allies_recruited", [])
            if recruits:
                pool = list(children_ctx.get("speaker_pool", []) or [])
                for recruit in recruits:
                    if recruit and recruit not in pool:
                        pool.append(recruit)
                if pool:
                    children_ctx["speaker_pool"] = pool

                # Beats에도 recruited 캐릭터 hint 추가
                beats = children_ctx.get("beats") or []
                if isinstance(beats, list) and beats:
                    enriched_beats = []
                    for beat in beats:
                        if isinstance(beat, dict):
                            beat_copy = dict(beat)
                            hints = beat_copy.get("speaker_hint")
                            if isinstance(hints, list):
                                hints = hints[:]
                            elif hints:
                                hints = [hints]
                            else:
                                hints = []
                            for recruit in recruits:
                                if recruit not in hints:
                                    hints.append(recruit)
                            beat_copy["speaker_hint"] = hints
                            enriched_beats.append(beat_copy)
                        else:
                            enriched_beats.append(beat)
                    children_ctx["beats"] = enriched_beats

        # RETURN_TO_FRONT 서사 프리롤
        return_stage_meta = metadata.get("return_stage") or {}
        return_stage_tag = str(return_stage_meta.get("stage_tag") or "").upper()
        temp_data = state.get("temp_data") or {}
        if return_stage_tag and stage_key_upper == return_stage_tag:
            queue_key = return_stage_meta.get("prefetch_queue_key", "mission_success_queue")
            queue = temp_data.get(queue_key) or []
            if queue:
                prefetch_list = children_ctx.setdefault("prefetch_dialogues", [])
                prefetch_list.extend(queue)

            token = return_stage_meta.get("prefetch_token")
            if token and not temp_data.get(token):
                narrative = ContextBuilderService._compose_return_to_front_dialogue(state, scenario, metadata)
                if narrative:
                    prefetch_list = children_ctx.setdefault("prefetch_dialogues", [])
                    prefetch_list.append(narrative)

        # Character refs 및 scenario_id 추가
        children_ctx.setdefault("character_refs", scenario.get("character_refs", {}))
        children_ctx.setdefault("scenario_id", scenario.get("scenario_id", "unknown"))

        # Fallback 처리
        if state.get("classification") in ("off_topic", "incoherent"):
            from src.tools import state_tools
            fallback_payload = state_tools.prepare_fallback(state, stage) if stage else None
            if fallback_payload:
                children_ctx["fallback"] = fallback_payload

        return children_ctx

    @staticmethod
    def _build_context_summary(state: Dict[str, Any]) -> Optional[str]:
        """최근 사용자 입력과 직전 대사들을 간단히 요약"""
        summary_lines: List[str] = []

        user_input = (state.get("user_input") or "").strip()
        if user_input:
            summary_lines.append(f"사용자: {user_input}")

        message_history = state.get("message_history") or []
        if isinstance(message_history, list):
            for entry in message_history[-4:]:
                if not isinstance(entry, dict):
                    continue
                speaker = entry.get("speaker") or entry.get("role") or "unknown"
                text = (entry.get("text") or entry.get("content") or "").strip()
                if text:
                    summary_lines.append(f"기록({speaker}): {text}")

        recent_dialogues = (state.get("output") or {}).get("dialogues") or []
        if isinstance(recent_dialogues, list):
            for dialogue in recent_dialogues[-2:]:
                if not isinstance(dialogue, dict):
                    continue
                speaker = dialogue.get("speaker") or "unknown"
                text = (dialogue.get("text") or dialogue.get("content") or "").strip()
                if text:
                    summary_lines.append(f"직전({speaker}): {text}")

        if not summary_lines:
            return None

        return "\n".join(summary_lines)

    @staticmethod
    def _collect_recent_dialogues(state: Dict[str, Any], limit: int = 4) -> List[str]:
        """LLM 프롬프트용으로 최근 대사 몇 줄을 정리"""
        recent_lines: List[str] = []
        history = state.get("message_history") or []
        if isinstance(history, list):
            for entry in history[-limit:]:
                if not isinstance(entry, dict):
                    continue
                speaker = entry.get("speaker") or entry.get("role") or "unknown"
                text = (entry.get("text") or entry.get("content") or "").strip()
                if text:
                    recent_lines.append(f"{speaker}: {text}")

        output_dialogues = (state.get("output") or {}).get("dialogues") or []
        if isinstance(output_dialogues, list):
            for dialogue in output_dialogues[-limit:]:
                if not isinstance(dialogue, dict):
                    continue
                speaker = dialogue.get("speaker") or "unknown"
                text = (dialogue.get("text") or dialogue.get("content") or "").strip()
                if text:
                    recent_lines.append(f"{speaker}: {text}")

        return recent_lines[-limit:]

    @staticmethod
    def _compose_return_to_front_dialogue(
        state: Dict[str, Any],
        scenario: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """RETURN_TO_FRONT 서사 대사 구성"""
        allies = state.get("allies_recruited", [])
        fails = state.get("recruit_failures", [])
        mission_meta = (metadata.get("mission") or {})
        name_map = mission_meta.get("ally_name_map") or {}
        dialogues = mission_meta.get("success_dialogues") or {}
        speaker = mission_meta.get("success_speaker", "tanjiro")
        fx = mission_meta.get("success_fx")

        def _display(names):
            converted = [name_map.get(name, name) for name in names]
            if not converted:
                return ""
            if len(converted) == 1:
                return converted[0]
            if len(converted) == 2:
                return f"{converted[0]}와 {converted[1]}"
            return ", ".join(converted[:-1]) + f" 그리고 {converted[-1]}"

        if allies and not fails:
            template = dialogues.get("allies")
            msg = template.format(allies=_display(allies)) if template else ""
        elif allies and fails:
            template = dialogues.get("partial")
            msg = template.format(allies=_display(allies), fails=_display(fails)) if template else ""
        else:
            template = dialogues.get("none")
            msg = template if template else ""

        if not msg:
            return None

        payload = {"speaker": speaker, "text": msg}
        if fx:
            payload["fx"] = fx
        return payload


__all__ = ["ContextBuilderService"]
