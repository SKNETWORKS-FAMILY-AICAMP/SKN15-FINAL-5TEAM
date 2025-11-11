"""
Game Feature UseCase
게임 요소 비즈니스 로직 계층
"""
from typing import List, Optional, Dict, Any
from uuid import UUID

from .repository import GameRepository
from .schemas import (
    UserEquipmentResponse,
    UserEquipmentUpdateRequest,
    UnlockedImageResponse,
    UnlockImageRequest,
    UnlockImageResponse,
    GalleryStatsResponse,
    RankDefinitionResponse,
    GameEventResponse,
    CreateGameEventRequest,
    MissionRecordResponse,
    CreateMissionRecordRequest,
    MissionStatsResponse
)


class GameUseCase:
    """게임 요소 UseCase"""

    def __init__(self, repository: GameRepository):
        self.repository = repository

    # ==================== Equipment ====================

    async def get_user_equipment(self, user_id: UUID) -> Optional[UserEquipmentResponse]:
        """사용자 장비 상태 조회"""
        equipment = await self.repository.get_user_equipment(user_id)

        if not equipment:
            # 장비가 없으면 초기화
            equipment = await self.repository.create_user_equipment(user_id)

        return UserEquipmentResponse.model_validate(equipment)

    async def update_user_equipment(
        self,
        user_id: UUID,
        update_data: UserEquipmentUpdateRequest
    ) -> Optional[UserEquipmentResponse]:
        """사용자 장비 업데이트"""
        # Pydantic 모델을 dict로 변환 (None 값 제외)
        equipment_updates = update_data.model_dump(exclude_none=True)

        if not equipment_updates:
            # 업데이트할 내용이 없으면 현재 상태 반환
            return await self.get_user_equipment(user_id)

        # 유효성 검증
        if 'sword_status' in equipment_updates:
            valid_sword = ['excellent', 'good', 'fair', 'poor', 'broken']
            if equipment_updates['sword_status'] not in valid_sword:
                raise ValueError(f"Invalid sword_status. Must be one of {valid_sword}")

        if 'uniform_status' in equipment_updates:
            valid_uniform = ['pristine', 'worn', 'equipped', 'damaged', 'torn']
            if equipment_updates['uniform_status'] not in valid_uniform:
                raise ValueError(f"Invalid uniform_status. Must be one of {valid_uniform}")

        if 'crow_status' in equipment_updates:
            valid_crow = ['waiting', 'active', 'resting', 'absent']
            if equipment_updates['crow_status'] not in valid_crow:
                raise ValueError(f"Invalid crow_status. Must be one of {valid_crow}")

        equipment = await self.repository.update_user_equipment(user_id, equipment_updates)

        if not equipment:
            return None

        return UserEquipmentResponse.model_validate(equipment)

    # ==================== Image Unlocks ====================

    async def unlock_image(
        self,
        user_id: UUID,
        unlock_data: UnlockImageRequest
    ) -> UnlockImageResponse:
        """이미지 획득 처리"""
        newly_unlocked = await self.repository.unlock_image_for_user(
            user_id=user_id,
            image_id=unlock_data.image_id,
            scenario_id=unlock_data.scenario_id,
            session_id=unlock_data.session_id,
            stage_id=unlock_data.stage_id,
            unlock_method=unlock_data.unlock_method
        )

        if newly_unlocked:
            # 새로 획득한 경우 상세 정보 조회
            unlocked_images = await self.repository.get_user_unlocked_images(
                user_id=user_id,
                scenario_id=unlock_data.scenario_id
            )
            # 가장 최근 획득한 이미지 찾기
            for img in unlocked_images:
                if img.image_id == unlock_data.image_id:
                    return UnlockImageResponse(
                        newly_unlocked=True,
                        unlock=UnlockedImageResponse.model_validate(img)
                    )

        return UnlockImageResponse(newly_unlocked=False)

    async def get_unlocked_images(
        self,
        user_id: UUID,
        scenario_id: Optional[str] = None
    ) -> List[UnlockedImageResponse]:
        """사용자가 획득한 이미지 목록 조회"""
        images = await self.repository.get_user_unlocked_images(user_id, scenario_id)
        return [UnlockedImageResponse.model_validate(img) for img in images]

    async def get_gallery_stats(
        self,
        user_id: UUID,
        scenario_id: Optional[str] = None,
        total_available: int = 100  # 기본값, 실제로는 image_assets에서 조회
    ) -> GalleryStatsResponse:
        """갤러리 통계 조회"""
        total_unlocked = await self.repository.get_unlock_count(user_id, scenario_id)

        unlock_percentage = (total_unlocked / total_available * 100) if total_available > 0 else 0.0

        return GalleryStatsResponse(
            total_unlocked=total_unlocked,
            total_available=total_available,
            unlock_percentage=round(unlock_percentage, 2)
        )

    async def check_image_unlocked(
        self,
        user_id: UUID,
        image_id: UUID
    ) -> bool:
        """특정 이미지 획득 여부 확인"""
        return await self.repository.check_image_unlocked(user_id, image_id)

    # ==================== Ranks ====================

    async def get_rank_by_code(self, rank_code: str) -> Optional[RankDefinitionResponse]:
        """랭크 코드로 랭크 조회"""
        rank = await self.repository.get_rank_by_code(rank_code)
        return RankDefinitionResponse.model_validate(rank) if rank else None

    async def get_rank_by_level(self, level: int) -> Optional[RankDefinitionResponse]:
        """레벨에 맞는 랭크 조회"""
        rank = await self.repository.get_rank_by_level(level)
        return RankDefinitionResponse.model_validate(rank) if rank else None

    async def get_all_ranks(self) -> List[RankDefinitionResponse]:
        """모든 랭크 조회"""
        ranks = await self.repository.get_all_ranks()
        return [RankDefinitionResponse.model_validate(rank) for rank in ranks]

    # ==================== Game Events ====================

    async def record_game_event(
        self,
        session_id: UUID,
        turn_number: int,
        event_data: CreateGameEventRequest
    ) -> GameEventResponse:
        """게임 이벤트 기록"""
        event = await self.repository.create_game_event(
            session_id=session_id,
            turn_number=turn_number,
            event_type=event_data.event_type,
            event_data=event_data.event_data
        )
        return GameEventResponse.model_validate(event)

    async def get_session_events(
        self,
        session_id: UUID,
        event_type: Optional[str] = None
    ) -> List[GameEventResponse]:
        """세션의 게임 이벤트 조회"""
        events = await self.repository.get_session_events(session_id, event_type)
        return [GameEventResponse.model_validate(event) for event in events]

    # ==================== Missions ====================

    async def record_mission(
        self,
        session_id: UUID,
        mission_data: CreateMissionRecordRequest
    ) -> MissionRecordResponse:
        """미션 기록"""
        record = await self.repository.create_mission_record(
            session_id=session_id,
            mission_type=mission_data.mission_type,
            target_character=mission_data.target_character,
            attempt_count=mission_data.attempt_count,
            success=mission_data.success
        )
        return MissionRecordResponse.model_validate(record)

    async def get_session_missions(self, session_id: UUID) -> List[MissionRecordResponse]:
        """세션의 미션 기록 조회"""
        missions = await self.repository.get_session_missions(session_id)
        return [MissionRecordResponse.model_validate(mission) for mission in missions]

    async def get_mission_stats(
        self,
        user_id: UUID,
        mission_type: Optional[str] = None
    ) -> MissionStatsResponse:
        """미션 통계 조회"""
        stats = await self.repository.get_user_mission_stats(user_id, mission_type)

        total = stats.get("total_missions", 0)
        successful = stats.get("successful_missions", 0)
        failed = stats.get("failed_missions", 0)

        success_rate = (successful / total * 100) if total > 0 else 0.0

        return MissionStatsResponse(
            total_missions=total,
            successful_missions=successful,
            failed_missions=failed,
            success_rate=round(success_rate, 2)
        )
