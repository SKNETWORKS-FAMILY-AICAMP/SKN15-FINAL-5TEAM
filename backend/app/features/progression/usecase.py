"""
Progression Feature UseCase
진행도 비즈니스 로직 계층
"""
from typing import List, Optional, Dict, Any
from uuid import UUID

from .repository import ProgressionRepository
from .schemas import (
    UserInputResponse,
    UserProgressionResponse,
    AwardXPRequest,
    AwardXPResponse,
    XPTransactionResponse,
    IncrementStatRequest,
    ScenarioProgressResponse,
    UpdateScenarioProgressRequest,
    ToggleLikeResponse,
    StageProgressionResponse,
    CreateStageProgressionRequest,
    UpdateStageProgressionRequest,
    UserProgressionWithRankResponse,
    UserStatsResponse
)


class ProgressionUseCase:
    """진행도 UseCase"""

    def __init__(self, repository: ProgressionRepository):
        self.repository = repository

    # ==================== UserInput ====================

    async def save_user_input(
        self,
        session_id: UUID,
        turn_number: int,
        user_input: str
    ) -> UserInputResponse:
        """사용자 입력 저장"""
        input_record = await self.repository.save_user_input(
            session_id, turn_number, user_input
        )
        return UserInputResponse.model_validate(input_record)

    async def get_user_inputs(
        self,
        session_id: UUID,
        limit: int = 10
    ) -> List[UserInputResponse]:
        """세션의 사용자 입력 조회"""
        inputs = await self.repository.get_user_inputs(session_id, limit)
        return [UserInputResponse.model_validate(inp) for inp in inputs]

    # ==================== UserProgression ====================

    async def get_user_progression(
        self,
        user_id: UUID
    ) -> Optional[UserProgressionResponse]:
        """사용자 진행도 조회"""
        progression = await self.repository.get_user_progression(user_id)

        if not progression:
            # 진행도가 없으면 초기화
            progression = await self.repository.create_user_progression(user_id)

        return UserProgressionResponse.model_validate(progression)

    async def award_xp(
        self,
        user_id: UUID,
        request: AwardXPRequest,
        session_id: Optional[UUID] = None
    ) -> AwardXPResponse:
        """
        경험치 지급

        자동으로 레벨업 계산
        """
        # XP 타입 검증
        valid_xp_types = [
            'message', 'session_complete', 'scenario_complete',
            'achievement', 'daily_bonus', 'event'
        ]

        if request.xp_type not in valid_xp_types:
            raise ValueError(f"Invalid xp_type. Must be one of {valid_xp_types}")

        result = await self.repository.award_experience(
            user_id=user_id,
            xp_amount=request.xp_amount,
            xp_type=request.xp_type,
            description=request.description,
            metadata=request.metadata,
            session_id=session_id
        )

        return AwardXPResponse(**result)

    async def increment_stat(
        self,
        user_id: UUID,
        request: IncrementStatRequest
    ) -> bool:
        """통계 증가"""
        try:
            return await self.repository.increment_user_stat(
                user_id, request.stat_name, request.increment_by
            )
        except ValueError as e:
            raise ValueError(str(e))

    async def get_xp_transactions(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[XPTransactionResponse]:
        """경험치 거래 내역 조회"""
        transactions = await self.repository.get_xp_transactions(
            user_id, limit, offset
        )
        return [XPTransactionResponse.model_validate(tx) for tx in transactions]

    async def get_progression_with_rank(
        self,
        user_id: UUID
    ) -> UserProgressionWithRankResponse:
        """
        사용자 진행도 + 랭크 정보

        랭크 정보는 game feature에서 조회
        """
        from app.features.game.repository import GameRepository
        from app.features.game.usecase import GameUseCase

        progression = await self.repository.get_user_progression(user_id)
        if not progression:
            progression = await self.repository.create_user_progression(user_id)

        # 랭크 정보 조회
        game_repo = GameRepository(self.repository.db)
        game_usecase = GameUseCase(game_repo)
        rank = await game_usecase.get_rank_by_level(progression.level)

        return UserProgressionWithRankResponse(
            user_id=progression.user_id,
            rank_code=progression.rank_code,
            rank_name_ko=rank.rank_name_ko if rank else None,
            rank_icon_emoji=rank.icon_emoji if rank else None,
            experience_points=progression.experience_points,
            level=progression.level,
            total_messages=progression.total_messages,
            total_sessions=progression.total_sessions,
            total_play_minutes=progression.total_play_minutes,
            scenarios_completed=progression.scenarios_completed,
            achievements_count=progression.achievements_count,
            created_at=progression.created_at,
            updated_at=progression.updated_at
        )

    # ==================== UserScenarioProgress ====================

    async def get_scenario_progress(
        self,
        user_id: UUID,
        scenario_id: str
    ) -> Optional[ScenarioProgressResponse]:
        """시나리오 진행도 조회"""
        progress = await self.repository.get_scenario_progress(user_id, scenario_id)
        return ScenarioProgressResponse.model_validate(progress) if progress else None

    async def update_scenario_progress(
        self,
        user_id: UUID,
        scenario_id: str,
        request: UpdateScenarioProgressRequest
    ) -> ScenarioProgressResponse:
        """시나리오 진행도 업데이트"""
        # Pydantic 모델을 dict로 변환 (None 값 제외)
        updates = request.model_dump(exclude_none=True)

        if not updates:
            # 업데이트할 내용이 없으면 현재 상태 반환
            progress = await self.repository.get_scenario_progress(user_id, scenario_id)
            if not progress:
                # 진행도가 없으면 빈 진행도 생성
                updates = {"has_started": False, "has_completed": False}
            else:
                return ScenarioProgressResponse.model_validate(progress)

        progress = await self.repository.update_scenario_progress(
            user_id, scenario_id, updates
        )

        return ScenarioProgressResponse.model_validate(progress)

    async def toggle_scenario_like(
        self,
        user_id: UUID,
        scenario_id: str
    ) -> ToggleLikeResponse:
        """시나리오 좋아요 토글"""
        result = await self.repository.toggle_scenario_like(user_id, scenario_id)
        return ToggleLikeResponse(**result)

    async def get_all_scenario_progress(
        self,
        user_id: UUID
    ) -> List[ScenarioProgressResponse]:
        """사용자의 모든 시나리오 진행도"""
        progress_list = await self.repository.get_all_scenario_progress(user_id)
        return [ScenarioProgressResponse.model_validate(p) for p in progress_list]

    # ==================== StageProgression ====================

    async def start_stage(
        self,
        session_id: UUID,
        request: CreateStageProgressionRequest
    ) -> StageProgressionResponse:
        """스테이지 진행 시작"""
        progression = await self.repository.create_stage_progression(
            session_id, request.stage_id, request.stage_order
        )
        return StageProgressionResponse.model_validate(progression)

    async def update_stage(
        self,
        stage_progression_id: int,
        request: UpdateStageProgressionRequest
    ) -> Optional[StageProgressionResponse]:
        """스테이지 진행 업데이트"""
        updates = request.model_dump(exclude_none=True)

        if not updates:
            return None

        progression = await self.repository.update_stage_progression(
            stage_progression_id, updates
        )

        return StageProgressionResponse.model_validate(progression) if progression else None

    async def get_session_stages(
        self,
        session_id: UUID
    ) -> List[StageProgressionResponse]:
        """세션의 모든 스테이지 진행"""
        progressions = await self.repository.get_session_stage_progressions(session_id)
        return [StageProgressionResponse.model_validate(p) for p in progressions]

    async def get_current_stage(
        self,
        session_id: UUID
    ) -> Optional[StageProgressionResponse]:
        """현재 진행 중인 스테이지"""
        progression = await self.repository.get_current_stage_progression(session_id)
        return StageProgressionResponse.model_validate(progression) if progression else None

    # ==================== Combined Operations ====================

    async def get_user_stats(
        self,
        user_id: UUID
    ) -> UserStatsResponse:
        """사용자 통계 종합"""
        # Progression
        progression = await self.repository.get_user_progression(user_id)
        if not progression:
            progression = await self.repository.create_user_progression(user_id)

        # Recent XP transactions
        recent_xp = await self.repository.get_xp_transactions(user_id, limit=10)

        # Scenario progress
        all_progress = await self.repository.get_all_scenario_progress(user_id)
        scenario_count = len(all_progress)
        total_likes = sum(1 for p in all_progress if p.is_liked)

        return UserStatsResponse(
            progression=UserProgressionResponse.model_validate(progression),
            recent_xp_transactions=[
                XPTransactionResponse.model_validate(tx) for tx in recent_xp
            ],
            scenario_progress_count=scenario_count,
            total_likes=total_likes
        )

    async def on_message_sent(
        self,
        user_id: UUID,
        session_id: UUID,
        scenario_id: str,
        user_input: str,
        turn_number: int
    ) -> Dict[str, Any]:
        """
        메시지 전송 시 호출되는 통합 처리

        - 사용자 입력 저장
        - 통계 업데이트
        - 경험치 지급
        """
        # 1. 사용자 입력 저장
        await self.repository.save_user_input(session_id, turn_number, user_input)

        # 2. 메시지 카운트 증가
        await self.repository.increment_user_stat(user_id, 'total_messages', 1)

        # 3. 시나리오 진행도 업데이트
        progress = await self.repository.get_scenario_progress(user_id, scenario_id)
        if progress:
            await self.repository.update_scenario_progress(
                user_id,
                scenario_id,
                {
                    "total_messages": progress.total_messages + 1,
                    "last_session_id": str(session_id),
                    "last_played_at": progress.last_played_at or progress.created_at
                }
            )
        else:
            # 새로운 시나리오 시작
            await self.repository.update_scenario_progress(
                user_id,
                scenario_id,
                {
                    "has_started": True,
                    "total_messages": 1,
                    "last_session_id": str(session_id)
                }
            )

        # 4. 경험치 지급 (메시지당 5 XP)
        xp_result = await self.repository.award_experience(
            user_id=user_id,
            xp_amount=5,
            xp_type="message",
            description=f"Message sent in {scenario_id}",
            session_id=session_id
        )

        return {
            "input_saved": True,
            "xp_awarded": xp_result
        }
