"""
Progression Feature - Repository
사용자 진행 시스템 데이터 접근
Layer 3: Repository (4-Layer Architecture)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from .models import UserProgression, XPTransaction
from app.core.logging import get_repository_logger

logger = get_repository_logger("Progression")


# 레벨/랭크 계산 상수
XP_PER_LEVEL = 100  # 레벨당 필요 XP
XP_PER_MESSAGE = 10  # 메시지당 XP
XP_PER_SCENARIO_COMPLETE = 500  # 시나리오 완료 시 XP

RANK_THRESHOLDS = {
    "novice": 0,      # Level 1-9
    "explorer": 10,   # Level 10-24
    "veteran": 25,    # Level 25-49
    "master": 50,     # Level 50-74
    "legend": 75,     # Level 75-99
}


class ProgressionRepository:
    """
    [Layer 3] Repository
    책임: 진행 데이터 CRUD, XP/레벨 계산
    금지: 비즈니스 로직, HTTP 처리
    """

    def __init__(self, db: AsyncSession):
        """
        Repository 초기화

        Args:
            db: 데이터베이스 세션
        """
        self.db = db

    async def get_or_create_progression(self, user_id: str) -> UserProgression:
        """
        사용자 진행 정보 조회 (없으면 생성)

        Args:
            user_id: 사용자 ID

        Returns:
            UserProgression
        """
        # 조회
        result = await self.db.execute(
            select(UserProgression).where(UserProgression.user_id == user_id)
        )
        progression = result.scalar_one_or_none()

        # 없으면 생성
        if not progression:
            progression = UserProgression(
                user_id=user_id,
                rank_code="novice",
                experience_points=0,
                level=1,
                total_messages=0,
                total_sessions=0,
                total_play_minutes=0,
                scenarios_completed=0,
                achievements_count=0,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            self.db.add(progression)
            await self.db.flush()

            logger.info("get_or_create_progression", f"Progression created for user: {user_id}")

        return progression

    async def add_message_xp(self, user_id: str, message_count: int = 1) -> UserProgression:
        """
        메시지 작성 XP 추가

        Args:
            user_id: 사용자 ID
            message_count: 메시지 개수

        Returns:
            업데이트된 UserProgression
        """
        progression = await self.get_or_create_progression(user_id)

        # 변동 전 상태 저장
        level_before = progression.level
        xp_before = progression.experience_points

        # XP 추가
        xp_gained = XP_PER_MESSAGE * message_count
        progression.experience_points += xp_gained
        progression.total_messages += message_count

        # 레벨업 체크
        progression = await self._check_level_up(progression)

        # 레벨업 여부 확인
        did_level_up = progression.level > level_before

        # 랭크 업데이트
        progression.rank_code = self._calculate_rank(progression.level)

        progression.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        # XP Transaction 로깅
        await self._log_xp_transaction(
            user_id=user_id,
            xp_amount=xp_gained,
            xp_type="message",
            xp_balance_after=progression.experience_points,
            level_before=level_before,
            level_after=progression.level,
            did_level_up=did_level_up,
            description=f"Gained {xp_gained} XP from {message_count} message(s)",
            metadata={"message_count": message_count}
        )

        logger.info("add_message_xp", f"Added {xp_gained} XP (messages={message_count})",
                   user_id=user_id, new_xp=progression.experience_points, level=progression.level)

        return progression

    async def add_scenario_complete_xp(self, user_id: str, scenario_id: Optional[str] = None) -> UserProgression:
        """
        시나리오 완료 XP 추가

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID (optional)

        Returns:
            업데이트된 UserProgression
        """
        progression = await self.get_or_create_progression(user_id)

        # 변동 전 상태 저장
        level_before = progression.level

        # XP 추가
        progression.experience_points += XP_PER_SCENARIO_COMPLETE
        progression.scenarios_completed += 1

        # 레벨업 체크
        progression = await self._check_level_up(progression)

        # 레벨업 여부 확인
        did_level_up = progression.level > level_before

        # 랭크 업데이트
        progression.rank_code = self._calculate_rank(progression.level)

        progression.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        # XP Transaction 로깅
        await self._log_xp_transaction(
            user_id=user_id,
            xp_amount=XP_PER_SCENARIO_COMPLETE,
            xp_type="scenario_complete",
            xp_balance_after=progression.experience_points,
            level_before=level_before,
            level_after=progression.level,
            did_level_up=did_level_up,
            description=f"Completed scenario! +{XP_PER_SCENARIO_COMPLETE} XP",
            metadata={"scenario_id": scenario_id} if scenario_id else {}
        )

        logger.info("add_scenario_complete_xp", f"Scenario completed! +{XP_PER_SCENARIO_COMPLETE} XP",
                   user_id=user_id, scenarios_completed=progression.scenarios_completed)

        return progression

    async def increment_session_count(self, user_id: str) -> UserProgression:
        """
        세션 카운트 증가

        Args:
            user_id: 사용자 ID

        Returns:
            업데이트된 UserProgression
        """
        progression = await self.get_or_create_progression(user_id)

        progression.total_sessions += 1
        progression.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        logger.debug("increment_session_count", f"Session count: {progression.total_sessions}",
                    user_id=user_id)

        return progression

    async def _check_level_up(self, progression: UserProgression) -> UserProgression:
        """
        레벨업 체크 및 처리

        Args:
            progression: UserProgression 인스턴스

        Returns:
            업데이트된 UserProgression
        """
        # 현재 레벨에 필요한 총 XP 계산
        required_xp = progression.level * XP_PER_LEVEL

        while progression.experience_points >= required_xp and progression.level < 99:
            # 레벨업!
            progression.level += 1
            required_xp = progression.level * XP_PER_LEVEL

            logger.info("_check_level_up", f"🎉 Level UP! → {progression.level}",
                       user_id=progression.user_id, new_level=progression.level)

        return progression

    def _calculate_rank(self, level: int) -> str:
        """
        레벨에 따른 랭크 계산

        Args:
            level: 사용자 레벨

        Returns:
            랭크 코드 (novice/explorer/veteran/master/legend)
        """
        if level >= RANK_THRESHOLDS["legend"]:
            return "legend"
        elif level >= RANK_THRESHOLDS["master"]:
            return "master"
        elif level >= RANK_THRESHOLDS["veteran"]:
            return "veteran"
        elif level >= RANK_THRESHOLDS["explorer"]:
            return "explorer"
        else:
            return "novice"

    async def get_progression(self, user_id: str) -> Optional[UserProgression]:
        """
        사용자 진행 정보 조회

        Args:
            user_id: 사용자 ID

        Returns:
            UserProgression 또는 None
        """
        result = await self.db.execute(
            select(UserProgression).where(UserProgression.user_id == user_id)
        )
        return result.scalar_one_or_none()

    # ============================================================
    # XP Transaction Logging
    # ============================================================

    async def _log_xp_transaction(
        self,
        user_id: str,
        xp_amount: int,
        xp_type: str,
        xp_balance_after: int,
        level_before: int,
        level_after: int,
        did_level_up: bool,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> XPTransaction:
        """
        XP 변동 기록 생성 (내부 메서드)

        Args:
            user_id: 사용자 ID
            xp_amount: XP 변동량 (양수: 획득, 음수: 소비)
            xp_type: XP 타입
            xp_balance_after: 변동 후 XP 잔액
            level_before: 변동 전 레벨
            level_after: 변동 후 레벨
            did_level_up: 레벨업 여부
            description: 설명
            metadata: 추가 메타데이터

        Returns:
            XPTransaction
        """
        transaction = XPTransaction(
            user_id=user_id,
            xp_amount=xp_amount,
            xp_type=xp_type,
            xp_balance_after=xp_balance_after,
            level_before=level_before,
            level_after=level_after,
            did_level_up=did_level_up,
            description=description,
            metadata=metadata or {}
        )
        self.db.add(transaction)
        await self.db.flush()

        logger.info("_log_xp_transaction", f"XP transaction logged: {xp_type} +{xp_amount}",
                   user_id=user_id, level_up=did_level_up)

        return transaction

    async def get_xp_transactions(
        self,
        user_id: str,
        xp_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[XPTransaction]:
        """
        사용자 XP 거래 내역 조회

        Args:
            user_id: 사용자 ID
            xp_type: XP 타입 필터
            limit: 결과 개수
            offset: 오프셋

        Returns:
            XPTransaction 리스트
        """
        query = select(XPTransaction).where(XPTransaction.user_id == user_id)

        if xp_type:
            query = query.where(XPTransaction.xp_type == xp_type)

        query = query.order_by(XPTransaction.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        transactions = result.scalars().all()

        logger.debug("get_xp_transactions", f"Found {len(transactions)} transactions",
                    user_id=user_id, xp_type=xp_type)

        return list(transactions)

    async def get_xp_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        사용자 XP 통계 조회

        Args:
            user_id: 사용자 ID

        Returns:
            통계 딕셔너리
        """
        # 전체 XP 획득/소비 통계
        transactions = await self.get_xp_transactions(user_id, limit=1000)

        total_earned = sum(t.xp_amount for t in transactions if t.xp_amount > 0)
        total_spent = sum(abs(t.xp_amount) for t in transactions if t.xp_amount < 0)
        total_level_ups = sum(1 for t in transactions if t.did_level_up)

        # XP 타입별 통계
        by_type = {}
        for t in transactions:
            if t.xp_type not in by_type:
                by_type[t.xp_type] = {"count": 0, "total_xp": 0}
            by_type[t.xp_type]["count"] += 1
            by_type[t.xp_type]["total_xp"] += t.xp_amount

        return {
            "total_earned": total_earned,
            "total_spent": total_spent,
            "total_level_ups": total_level_ups,
            "by_type": by_type,
            "transaction_count": len(transactions)
        }
