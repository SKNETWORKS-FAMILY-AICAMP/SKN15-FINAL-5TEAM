"""
Stage Service - 스테이지 진행 관리
시나리오 스테이지의 흐름과 전환을 관리
"""
from typing import Dict, Any, Optional, List
from app.core.logging import get_parent_logger

logger = get_parent_logger("StageService")


class StageDefinition:
    """
    스테이지 정의 클래스

    간소화된 스테이지 구조
    """
    def __init__(
        self,
        stage_id: str,
        stage_type: str = "scene",
        description: str = "",
        beats: Optional[List[Dict[str, Any]]] = None,
        next_stage: Optional[str] = None,
        auto_advance: bool = False
    ):
        self.stage_id = stage_id
        self.stage_type = stage_type  # scene, mission, free_intent, router, open_narrative
        self.description = description
        self.beats = beats or []
        self.next_stage = next_stage
        self.auto_advance = auto_advance


class StageService:
    """
    스테이지 관리 서비스

    책임:
    - 스테이지 정의 관리
    - 스테이지 전환 로직
    - 완료 조건 판단
    - 다음 스테이지 결정
    - Beat 기반 대화 지원
    """

    def __init__(self):
        """StageService 초기화"""
        # 하드코딩된 간단한 스테이지 정의 (향후 YAML에서 로드)
        self.stages = self._init_default_stages()
        logger.info("__init__", "StageService initialized", stages_count=len(self.stages))

    def register_stage(self, stage: StageDefinition):
        """
        동적으로 스테이지 등록 (시나리오 로드 시 사용)

        Args:
            stage: StageDefinition 객체
        """
        self.stages[stage.stage_id] = stage
        logger.info("register_stage", f"Stage registered: {stage.stage_id}", beats_count=len(stage.beats))

    def _init_default_stages(self) -> Dict[str, StageDefinition]:
        """
        기본 스테이지 정의 (하드코딩)

        향후: YAML 파일에서 로드
        """
        return {
            "intro": StageDefinition(
                stage_id="intro",
                stage_type="scene",
                description="인트로 장면",
                beats=[
                    {
                        "beat_id": "greeting",
                        "description": "캐릭터가 플레이어를 환영한다",
                        "goal": "첫 만남"
                    }
                ],
                next_stage="main",
                auto_advance=False
            ),
            "main": StageDefinition(
                stage_id="main",
                stage_type="open_narrative",
                description="자유 대화",
                beats=[],
                next_stage=None,
                auto_advance=False
            ),
        }

    def get_stage(self, stage_id: str) -> Optional[StageDefinition]:
        """
        스테이지 정의 가져오기

        Args:
            stage_id: 스테이지 ID

        Returns:
            StageDefinition 또는 None
        """
        stage = self.stages.get(stage_id)

        if not stage:
            logger.warning("get_stage", f"Stage not found: {stage_id}")
            # Fallback: 기본 스테이지
            return self.stages.get("main")

        return stage

    def resolve_stage(self, state: Dict[str, Any]) -> StageDefinition:
        """
        현재 상태에서 스테이지 결정

        Args:
            state: 세션 상태

        Returns:
            StageDefinition
        """
        current_stage_id = state.get("current_stage", "intro")
        stage = self.get_stage(current_stage_id)

        if not stage:
            # Fallback
            logger.warning("resolve_stage", f"Stage resolution failed, using 'main'")
            stage = self.stages["main"]

        logger.info(
            "resolve_stage",
            "Stage resolved",
            stage_id=stage.stage_id,
            stage_type=stage.stage_type
        )

        return stage

    def check_stage_complete(
        self,
        stage: StageDefinition,
        state: Dict[str, Any]
    ) -> bool:
        """
        스테이지 완료 조건 확인

        Args:
            stage: 스테이지 정의
            state: 현재 상태

        Returns:
            완료 여부
        """
        stage_turn = state.get("stage_turn", 0)

        # 기본 완료 조건: 3턴 이상
        if stage_turn >= 3:
            logger.info(
                "check_stage_complete",
                "Stage complete by turn count",
                stage_id=stage.stage_id,
                stage_turn=stage_turn
            )
            return True

        # auto_advance 플래그 체크
        if stage.auto_advance:
            logger.info(
                "check_stage_complete",
                "Stage complete by auto_advance",
                stage_id=stage.stage_id
            )
            return True

        # scene 상태에서 완료 플래그 체크
        scene_state = state.get("scene", {})
        if scene_state.get("stage_completed"):
            logger.info(
                "check_stage_complete",
                "Stage complete by scene flag",
                stage_id=stage.stage_id
            )
            return True

        return False

    def get_next_stage(
        self,
        current_stage: StageDefinition,
        state: Dict[str, Any]
    ) -> Optional[str]:
        """
        다음 스테이지 결정

        Args:
            current_stage: 현재 스테이지
            state: 현재 상태

        Returns:
            다음 스테이지 ID 또는 None
        """
        # 1. 스테이지 정의에서 next_stage 확인
        if current_stage.next_stage:
            logger.info(
                "get_next_stage",
                "Next stage from definition",
                current=current_stage.stage_id,
                next=current_stage.next_stage
            )
            return current_stage.next_stage

        # 2. game 상태에서 pending_stage 확인
        game_state = state.get("game", {})
        pending = game_state.get("pending_stage")
        if pending:
            logger.info(
                "get_next_stage",
                "Next stage from pending",
                current=current_stage.stage_id,
                next=pending
            )
            return pending

        # 3. 다음 스테이지 없음
        logger.info(
            "get_next_stage",
            "No next stage",
            current=current_stage.stage_id
        )
        return None

    def should_advance_now(
        self,
        stage: StageDefinition,
        stage_complete: bool,
        next_stage: Optional[str]
    ) -> bool:
        """
        즉시 스테이지를 전환해야 하는지 판단

        Args:
            stage: 현재 스테이지
            stage_complete: 스테이지 완료 여부
            next_stage: 다음 스테이지 ID

        Returns:
            즉시 전환 여부
        """
        # router 타입은 항상 즉시 전환
        if stage.stage_type == "router":
            return True

        # 완료되지 않았으면 전환 안함
        if not stage_complete:
            return False

        # 다음 스테이지가 없으면 전환 안함
        if not next_stage:
            return False

        # auto_advance 플래그 확인
        if stage.auto_advance:
            return True

        # 기본: 완료되었고 다음 스테이지가 있으면 전환
        return True

    def get_stats(self) -> Dict[str, Any]:
        """
        서비스 통계

        Returns:
            통계 dict
        """
        return {
            "total_stages": len(self.stages),
            "stage_ids": list(self.stages.keys()),
        }
