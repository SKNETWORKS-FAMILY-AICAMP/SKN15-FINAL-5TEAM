"""
Affinity Repository
친밀도 관련 DB 접근 레이어
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional, List
from datetime import datetime

from ..models import (
    AffinityRecord,
    UserCharacterAffinity,
)
from app.core.logging import get_repository_logger

logger = get_repository_logger("Affinity")


class AffinityRepository:
    """
    친밀도 CRUD 전담 Repository
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_affinity_record(
        self,
        session_id: str,
        turn_number: int,
        character_name: str,
        affinity_score: int,
        change_amount: Optional[int] = None
    ) -> AffinityRecord:
        """
        세션별 친밀도 변화 기록 저장

        Args:
            session_id: 세션 ID
            turn_number: 턴 번호
            character_name: 캐릭터 이름
            affinity_score: 현재 친밀도 점수
            change_amount: 변화량

        Returns:
            저장된 AffinityRecord
        """
        logger.info("save_affinity_record", f"Saving affinity for {character_name}",
                   session_id=session_id, score=affinity_score)

        record = AffinityRecord(
            session_id=session_id,
            turn_number=turn_number,
            character_name=character_name,
            affinity_score=affinity_score,
            change_amount=change_amount
        )
        self.db.add(record)
        await self.db.flush()

        logger.info("save_affinity_record", f"Affinity record saved", record_id=record.id)
        return record

    async def get_latest_affinity(
        self,
        session_id: str,
        character_name: str
    ) -> Optional[AffinityRecord]:
        """
        세션의 최신 친밀도 기록 조회

        Args:
            session_id: 세션 ID
            character_name: 캐릭터 이름

        Returns:
            최신 AffinityRecord (없으면 None)
        """
        logger.debug("get_latest_affinity", f"Fetching latest affinity for {character_name}",
                    session_id=session_id)

        stmt = (
            select(AffinityRecord)
            .where(
                and_(
                    AffinityRecord.session_id == session_id,
                    AffinityRecord.character_name == character_name
                )
            )
            .order_by(AffinityRecord.timestamp.desc())
            .limit(1)
        )

        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()

        logger.debug("get_latest_affinity", f"Latest affinity: {record.affinity_score if record else None}")
        return record

    async def upsert_user_character_affinity(
        self,
        user_id: str,
        character_name: str,
        score_delta: int
    ) -> UserCharacterAffinity:
        """
        사용자별 글로벌 친밀도 UPSERT

        Args:
            user_id: 사용자 ID
            character_name: 캐릭터 이름
            score_delta: 친밀도 변화량

        Returns:
            업데이트된 UserCharacterAffinity
        """
        logger.info("upsert_user_character_affinity", f"Updating global affinity for {character_name}",
                   user_id=user_id, delta=score_delta)

        # 기존 레코드 조회
        stmt = select(UserCharacterAffinity).where(
            and_(
                UserCharacterAffinity.user_id == user_id,
                UserCharacterAffinity.character_name == character_name
            )
        )
        result = await self.db.execute(stmt)
        affinity = result.scalar_one_or_none()

        if affinity:
            # 업데이트
            affinity.total_affinity_score = max(0, min(1000, affinity.total_affinity_score + score_delta))
            affinity.total_interactions += 1
            affinity.last_interaction_at = datetime.utcnow()
            affinity.updated_at = datetime.utcnow()
        else:
            # 생성
            affinity = UserCharacterAffinity(
                user_id=user_id,
                character_name=character_name,
                total_affinity_score=max(0, min(1000, score_delta)),
                affinity_level=1,
                total_interactions=1
            )
            self.db.add(affinity)

        await self.db.flush()
        logger.info("upsert_user_character_affinity", f"Global affinity updated",
                   user_id=user_id, new_score=affinity.total_affinity_score)
        return affinity

    async def get_user_character_affinity(
        self,
        user_id: str,
        character_name: str
    ) -> Optional[UserCharacterAffinity]:
        """
        사용자의 특정 캐릭터 친밀도 조회

        Args:
            user_id: 사용자 ID
            character_name: 캐릭터 이름

        Returns:
            UserCharacterAffinity (없으면 None)
        """
        logger.debug("get_user_character_affinity", f"Fetching affinity for {character_name}",
                    user_id=user_id)

        stmt = select(UserCharacterAffinity).where(
            and_(
                UserCharacterAffinity.user_id == user_id,
                UserCharacterAffinity.character_name == character_name
            )
        )

        result = await self.db.execute(stmt)
        affinity = result.scalar_one_or_none()

        logger.debug("get_user_character_affinity", f"Affinity found: {affinity is not None}")
        return affinity

    async def get_all_user_affinities(
        self,
        user_id: str
    ) -> List[UserCharacterAffinity]:
        """
        사용자의 모든 캐릭터 친밀도 조회

        Args:
            user_id: 사용자 ID

        Returns:
            List[UserCharacterAffinity] (없으면 빈 리스트)
        """
        logger.debug("get_all_user_affinities", "Fetching all affinities", user_id=user_id)

        stmt = select(UserCharacterAffinity).where(
            UserCharacterAffinity.user_id == user_id
        ).order_by(UserCharacterAffinity.total_affinity_score.desc())

        result = await self.db.execute(stmt)
        affinities = result.scalars().all()

        logger.debug("get_all_user_affinities", f"Found {len(affinities)} affinities")
        return list(affinities)
