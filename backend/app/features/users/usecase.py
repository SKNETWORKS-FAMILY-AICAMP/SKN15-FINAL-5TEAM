"""
Users Feature - UseCase
사용자 프로필 및 통계 비즈니스 로직
Layer 2: UseCase (4-Layer Architecture)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.core.logging import get_usecase_logger
from .repository import UserRepository
from app.features.chat.repositories import AffinityRepository, MemoryRepository
from app.features.galleries.repository import GalleryRepository

logger = get_usecase_logger("User")


class UserUseCase:
    """
    [Layer 2] UseCase
    책임: 사용자 관리 비즈니스 로직, 트랜잭션 경계
    금지: DB 직접 접근 (Repository 사용), HTTP 처리 (Controller가 담당)
    """

    def __init__(self, db: AsyncSession):
        """
        UseCase 초기화

        Args:
            db: 데이터베이스 세션 (Controller에서 주입)
        """
        self.db = db
        self.repository = UserRepository(db)
        self.affinity_repository = AffinityRepository(db)
        self.memory_repository = MemoryRepository(db)
        self.gallery_repository = GalleryRepository(db)

    async def get_user_profile(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        사용자 프로필 조회 (캐릭터 호감도 포함)

        Args:
            user_id: 사용자 ID

        Returns:
            사용자 프로필 정보
            {
                "user_id": str,
                "username": str,
                "display_name": str,
                "email": str,
                "credits": int,
                "created_at": str,
                "updated_at": str,
                "affinities": List[Dict]  # 캐릭터 호감도 목록
            }
        """
        logger.info("get_user_profile", "Getting user profile", user_id=user_id)

        # Repository로 사용자 조회
        user = await self.repository.get_user_by_id(user_id)
        if not user:
            logger.warning("get_user_profile", "User not found", user_id=user_id)
            return None

        # AffinityRepository로 모든 캐릭터 호감도 조회
        affinities = await self.affinity_repository.get_all_user_affinities(user_id)

        # 호감도 정보를 Dict 리스트로 변환
        affinity_list = []
        for affinity in affinities:
            affinity_list.append({
                "character_name": affinity.character_name,
                "total_affinity_score": affinity.total_affinity_score,
                "affinity_level": affinity.affinity_level,
                "total_interactions": affinity.total_interactions,
                "last_interaction_at": affinity.last_interaction_at.isoformat() if affinity.last_interaction_at else None
            })

        # 사용자 프로필에 호감도 정보 추가
        user["affinities"] = affinity_list

        logger.info("get_user_profile", "Profile retrieved with affinities",
                   user_id=user_id, affinity_count=len(affinity_list))
        return user

    async def update_user_profile(
        self,
        user_id: str,
        display_name: Optional[str] = None,
        email: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        사용자 프로필 수정

        Args:
            user_id: 사용자 ID
            display_name: 표시 이름 (선택적)
            email: 이메일 (선택적)

        Returns:
            수정된 프로필 정보
        """
        logger.info("update_user_profile", "Updating user profile",
                   user_id=user_id)

        # 수정할 필드 구성
        updates = {}
        if display_name is not None:
            updates["display_name"] = display_name
        if email is not None:
            updates["email"] = email

        if not updates:
            logger.warning("update_user_profile", "No fields to update")
            return await self.get_user_profile(user_id)

        # Repository로 프로필 업데이트
        success = await self.repository.update_user_profile(
            user_id,
            display_name=updates.get("display_name"),
            email=updates.get("email")
        )

        if not success:
            logger.warning("update_user_profile", "Update failed", user_id=user_id)
            return None

        logger.info("update_user_profile", "Profile updated",
                   user_id=user_id, fields=list(updates.keys()))

        # 업데이트된 프로필 반환
        return await self.get_user_profile(user_id)

    async def get_user_stats(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        사용자 통계 조회

        Args:
            user_id: 사용자 ID

        Returns:
            사용자 통계
            {
                "total_dialogues": int,  # 총 대화 수
                "total_sessions": int,  # 총 세션 수
                "completed_scenarios": int,  # 완료한 시나리오 수
                "total_credits_used": int,  # 사용한 크레딧
                "total_affinity_points": int,  # 총 친밀도 점수
                "achievements": List[str],  # 달성한 업적
                "rank": str,  # 사용자 등급
                "created_at": str,  # 가입일
                "last_active_at": str  # 마지막 활동
            }
        """
        logger.info("get_user_stats", "Getting user stats", user_id=user_id)

        # Repository로 통계 조회
        stats = await self.repository.get_user_stats(user_id)

        if not stats:
            # 사용자가 없으면 기본값 반환
            stats = {
                "total_sessions": 0,
                "total_bubbles": 0,
                "current_credits": 0,
                "active_sessions": 0,
                "last_session_at": None
            }

        logger.info("get_user_stats", "Stats retrieved", user_id=user_id)
        return stats

    async def get_user_credits(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        사용자 크레딧 조회

        Args:
            user_id: 사용자 ID

        Returns:
            크레딧 정보
        """
        logger.info("get_user_credits", "Getting user credits", user_id=user_id)

        credits = await self.repository.get_user_credits(user_id)

        logger.info("get_user_credits", "Credits retrieved", user_id=user_id)
        return credits

    async def consume_user_credits(
        self,
        user_id: str,
        amount: int,
        description: str
    ) -> Dict[str, Any]:
        """
        사용자 크레딧 소비

        Args:
            user_id: 사용자 ID
            amount: 소비할 양
            description: 사용 목적

        Returns:
            소비 결과
        """
        logger.info("consume_user_credits", "Consuming credits",
                   user_id=user_id, amount=amount)

        # 크레딧 소비
        success = await self.repository.consume_credits(user_id, amount, description)

        if not success:
            logger.warning("consume_user_credits", "Failed to consume credits",
                          user_id=user_id, amount=amount)
            return {
                "success": False,
                "message": "Insufficient credits",
                "remaining_credits": 0
            }

        # 남은 크레딧 조회
        credits = await self.repository.get_user_credits(user_id)

        logger.info("consume_user_credits", "Credits consumed successfully",
                   user_id=user_id, amount=amount)

        return {
            "success": True,
            "message": "Credits consumed successfully",
            "remaining_credits": credits["bubble_count"]
        }

    async def get_my_gallery_images(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        내 갤러리 이미지 목록 조회 (마이페이지)

        Args:
            user_id: 사용자 ID
            limit: 페이징 크기
            offset: 페이징 오프셋

        Returns:
            이미지 목록 (통계 정보 포함)
            [
                {
                    "image_id": str,
                    "user_id": str,
                    "scenario_id": str,
                    "session_id": str,
                    "stage_tag": str,
                    "image_url": str,
                    "image_type": str,
                    "extra_metadata": Dict,
                    "created_at": str,
                    "like_count": int,
                    "view_count": int,
                    "user_liked": bool
                },
                ...
            ]
        """
        logger.info("get_my_gallery_images", "Getting gallery images",
                   user_id=user_id, limit=limit, offset=offset)

        # Repository로 이미지 목록 조회 (통계 정보 포함)
        images_with_stats = await self.gallery_repository.get_images_by_user_id(
            user_id=user_id,
            limit=limit,
            offset=offset
        )

        # Tuple (GalleryImage, like_count, view_count, user_liked) → Dict 변환
        images = []
        for img, like_count, view_count, user_liked in images_with_stats:
            image_dict = {
                "image_id": str(img.image_id),
                "user_id": str(img.user_id),
                "scenario_id": img.scenario_id,
                "session_id": str(img.session_id) if img.session_id else None,
                "stage_tag": img.stage_tag,
                "image_url": img.image_url,
                "image_type": img.image_type,
                "generation_prompt": img.generation_prompt,
                "generation_model": img.generation_model,
                "extra_metadata": img.extra_metadata,
                "is_unlocked": img.is_unlocked,
                "is_favorite": img.is_favorite,
                "created_at": img.created_at.isoformat() if img.created_at else None,
                "unlocked_at": img.unlocked_at.isoformat() if img.unlocked_at else None,
                "like_count": like_count,
                "view_count": view_count,
                "user_liked": user_liked
            }
            images.append(image_dict)

        logger.info("get_my_gallery_images", f"Retrieved {len(images)} images",
                   user_id=user_id)

        return images

    async def get_my_progression(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        사용자 진행도 조회 (XP/Level/Rank)

        Args:
            user_id: 사용자 ID

        Returns:
            진행도 정보
            {
                "user_id": str,
                "rank_code": str,
                "rank_name_ko": str,
                "rank_name_en": str,
                "rank_name_ja": str,
                "icon_emoji": str,
                "level": int,
                "experience_points": int,
                "total_messages": int,
                "total_sessions": int,
                "total_play_minutes": int,
                "scenarios_completed": int,
                "achievements_count": int,
                "min_xp": int,
                "description_ko": str
            }
        """
        logger.info("get_my_progression", "Getting user progression", user_id=user_id)

        # Repository로 진행도 조회
        progression = await self.repository.get_progression_by_user_id(user_id)

        if not progression:
            logger.warning("get_my_progression", "Progression not found", user_id=user_id)
            return None

        logger.info("get_my_progression", "Progression retrieved",
                   user_id=user_id, level=progression.get("level"), rank=progression.get("rank_code"))

        return progression

    async def get_my_memories(
        self,
        user_id: str,
        scenario_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        내 기억 조회

        Args:
            user_id: 사용자 ID
            scenario_id: 시나리오 ID (선택)
            memory_type: 기억 유형 (선택: episodic/semantic/procedural)
            limit: 최대 개수

        Returns:
            기억 목록
        """
        logger.info("get_my_memories", "Getting user memories",
                   user_id=user_id, scenario_id=scenario_id, memory_type=memory_type)

        # MemoryRepository로 기억 조회
        memories = await self.memory_repository.get_user_memories(
            user_id=user_id,
            scenario_id=scenario_id,
            memory_type=memory_type,
            limit=limit
        )

        # ORM 객체를 Dict로 변환
        memory_list = []
        for memory in memories:
            memory_dict = {
                "memory_id": memory.memory_id,
                "user_id": str(memory.user_id),
                "scenario_id": memory.scenario_id,
                "memory_type": memory.memory_type,
                "content": memory.content,
                "importance_score": memory.importance_score,
                "access_count": memory.access_count,
                "last_accessed_at": memory.last_accessed_at.isoformat() if memory.last_accessed_at else None,
                "created_at": memory.created_at.isoformat() if memory.created_at else None,
                "updated_at": memory.updated_at.isoformat() if memory.updated_at else None
            }
            memory_list.append(memory_dict)

        logger.info("get_my_memories", f"Retrieved {len(memory_list)} memories",
                   user_id=user_id)

        return memory_list

    async def get_my_settings(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        사용자 설정 조회

        Args:
            user_id: 사용자 ID

        Returns:
            사용자 설정 정보 (없으면 기본값 반환)
        """
        logger.info("get_my_settings", "Getting user settings", user_id=user_id)

        # Repository로 설정 조회
        settings = await self.repository.get_settings_by_user_id(user_id)

        # 설정이 없으면 기본값 생성하여 반환
        if not settings:
            logger.info("get_my_settings", "No settings found, creating default", user_id=user_id)

            # 기본 설정 생성
            default_settings = {
                "sound_enabled": True,
                "bgm_volume": 80,
                "sfx_volume": 100,
                "language": "ko"
            }

            # DB에 저장
            await self.repository.upsert_user_settings(user_id, default_settings)

            # 생성된 설정 조회
            settings = await self.repository.get_settings_by_user_id(user_id)

        logger.info("get_my_settings", "Settings retrieved", user_id=user_id)
        return settings

    async def update_my_settings(
        self,
        user_id: str,
        settings_update: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        사용자 설정 업데이트

        Args:
            user_id: 사용자 ID
            settings_update: 업데이트할 설정 데이터

        Returns:
            업데이트된 설정 정보
        """
        logger.info("update_my_settings", "Updating user settings",
                   user_id=user_id, fields=list(settings_update.keys()))

        # Repository로 설정 업데이트 (UPSERT)
        await self.repository.upsert_user_settings(user_id, settings_update)

        # 업데이트된 설정 조회
        settings = await self.repository.get_settings_by_user_id(user_id)

        logger.info("update_my_settings", "Settings updated", user_id=user_id)
        return settings

    # ========================================
    # 크레딧 트랜잭션 관련 비즈니스 로직
    # ========================================

    async def create_credit_transaction(
        self,
        user_id: str,
        amount: int,
        transaction_type: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        크레딧 트랜잭션 생성

        Args:
            user_id: 사용자 ID
            amount: 변동량 (양수: 획득, 음수: 소비)
            transaction_type: 트랜잭션 타입 (purchase, consume, refund, bonus, initial)
            description: 설명

        Returns:
            생성된 트랜잭션 정보
        """
        logger.info("create_credit_transaction", "Creating transaction",
                   user_id=user_id, amount=amount, type=transaction_type)

        # 트랜잭션 타입 검증
        valid_types = ['purchase', 'consume', 'refund', 'bonus', 'initial']
        if transaction_type not in valid_types:
            logger.error("create_credit_transaction", "Invalid transaction type",
                        type=transaction_type, valid=valid_types)
            raise ValueError(f"Invalid transaction type. Must be one of: {valid_types}")

        # Repository로 트랜잭션 생성 (잔액 자동 계산 및 업데이트)
        try:
            transaction = await self.repository.create_credit_transaction(
                user_id=user_id,
                amount=amount,
                transaction_type=transaction_type,
                description=description
            )

            logger.info("create_credit_transaction", "Transaction created successfully",
                       transaction_id=transaction["transaction_id"],
                       balance_after=transaction["balance_after"])

            return transaction

        except ValueError as e:
            # 잔액 부족 등의 에러
            logger.error("create_credit_transaction", "Transaction failed", error=str(e))
            raise

        except Exception as e:
            logger.error("create_credit_transaction", "Unexpected error", error=str(e))
            raise

    async def get_my_credit_transactions(
        self,
        user_id: str,
        transaction_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        사용자의 크레딧 트랜잭션 조회

        Args:
            user_id: 사용자 ID
            transaction_type: 트랜잭션 타입 필터 (선택)
            limit: 조회 개수

        Returns:
            트랜잭션 리스트
        """
        logger.info("get_my_credit_transactions", "Getting transactions",
                   user_id=user_id, type=transaction_type, limit=limit)

        transactions = await self.repository.get_credit_transactions(
            user_id=user_id,
            transaction_type=transaction_type,
            limit=limit
        )

        # Note: datetime is already converted to string in repository layer

        logger.info("get_my_credit_transactions", f"Retrieved {len(transactions)} transactions",
                   user_id=user_id)

        return transactions

    async def get_my_credit_stats(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        사용자의 크레딧 트랜잭션 통계 조회

        Args:
            user_id: 사용자 ID

        Returns:
            통계 정보
        """
        logger.info("get_my_credit_stats", "Getting credit stats", user_id=user_id)

        stats = await self.repository.get_credit_transaction_stats(user_id)

        logger.info("get_my_credit_stats", "Stats retrieved",
                   user_id=user_id, total=stats["total_transactions"])

        return stats

    async def purchase_credits(
        self,
        user_id: str,
        amount: int,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        크레딧 구매 (편의 메서드)

        Args:
            user_id: 사용자 ID
            amount: 구매할 크레딧 수
            description: 설명

        Returns:
            트랜잭션 정보
        """
        if amount <= 0:
            raise ValueError("Purchase amount must be positive")

        return await self.create_credit_transaction(
            user_id=user_id,
            amount=amount,
            transaction_type="purchase",
            description=description or f"크레딧 구매: {amount}개"
        )

    async def consume_credits(
        self,
        user_id: str,
        amount: int,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        크레딧 소비 (편의 메서드)

        Args:
            user_id: 사용자 ID
            amount: 소비할 크레딧 수
            description: 설명

        Returns:
            트랜잭션 정보
        """
        if amount <= 0:
            raise ValueError("Consume amount must be positive")

        return await self.create_credit_transaction(
            user_id=user_id,
            amount=-amount,  # 음수로 변환
            transaction_type="consume",
            description=description or f"크레딧 사용: {amount}개"
        )

    async def refund_credits(
        self,
        user_id: str,
        amount: int,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        크레딧 환불 (편의 메서드)

        Args:
            user_id: 사용자 ID
            amount: 환불할 크레딧 수
            description: 설명

        Returns:
            트랜잭션 정보
        """
        if amount <= 0:
            raise ValueError("Refund amount must be positive")

        return await self.create_credit_transaction(
            user_id=user_id,
            amount=amount,
            transaction_type="refund",
            description=description or f"크레딧 환불: {amount}개"
        )

    async def grant_bonus_credits(
        self,
        user_id: str,
        amount: int,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        보너스 크레딧 지급 (편의 메서드)

        Args:
            user_id: 사용자 ID
            amount: 지급할 크레딧 수
            description: 설명

        Returns:
            트랜잭션 정보
        """
        if amount <= 0:
            raise ValueError("Bonus amount must be positive")

        return await self.create_credit_transaction(
            user_id=user_id,
            amount=amount,
            transaction_type="bonus",
            description=description or f"보너스 크레딧: {amount}개"
        )
