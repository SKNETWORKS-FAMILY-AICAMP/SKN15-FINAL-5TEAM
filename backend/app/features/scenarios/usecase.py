"""
Scenarios Feature - UseCase
시나리오 목록, 상세, 댓글, 좋아요 비즈니스 로직
Layer 2: UseCase (4-Layer Architecture)
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from .repository import ScenarioRepository
from .models import ScenarioComment
from app.features.chat.services import ScenarioService
from app.core.logging import get_usecase_logger

logger = get_usecase_logger("Scenario")


class ScenarioUseCase:
    """
    [Layer 2] UseCase
    책임: 시나리오 비즈니스 로직, 트랜잭션 경계
    금지: DB 직접 접근 (Repository 사용), HTTP 처리 (Controller가 담당)
    """

    def __init__(self, db: AsyncSession):
        """
        UseCase 초기화

        Args:
            db: 데이터베이스 세션 (Controller에서 주입)
        """
        self.db = db
        self.repository = ScenarioRepository(db)
        self.scenario_service = ScenarioService()

    async def list_scenarios(
        self,
        user_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        시나리오 목록 조회

        ScenarioService를 통해 시나리오 목록을 가져오고,
        Repository를 통해 좋아요 정보를 추가합니다.

        Args:
            user_id: 사용자 ID (좋아요 정보 조회용, 선택적)
            limit: 페이징 크기
            offset: 페이징 오프셋

        Returns:
            시나리오 목록 (좋아요 정보 포함)
        """
        logger.info("list_scenarios", "Listing scenarios", limit=limit, offset=offset)

        # ScenarioService로 시나리오 목록 가져오기
        all_scenarios = self.scenario_service.list_scenarios()

        # 페이징 적용
        scenarios = all_scenarios[offset:offset + limit]

        # 각 시나리오에 좋아요 정보 추가
        result = []
        for scenario in scenarios:
            scenario_id = scenario.get("scenario_id")

            # 좋아요 개수 조회
            like_count = await self.repository.get_scenario_like_count(scenario_id)

            # 사용자 좋아요 여부 확인
            user_liked = False
            if user_id:
                user_liked = await self.repository.check_user_liked_scenario(
                    scenario_id, user_id
                )

            # 시나리오 정보에 좋아요 정보 추가
            scenario_with_likes = {
                **scenario,
                "like_count": like_count,
                "user_liked": user_liked
            }
            result.append(scenario_with_likes)

        logger.info("list_scenarios", f"Retrieved {len(result)} scenarios")
        return result

    async def get_scenario_detail(
        self,
        scenario_id: str,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        시나리오 상세 조회

        ScenarioService를 통해 시나리오 상세 정보를 가져오고,
        Repository를 통해 좋아요 및 댓글 정보를 추가합니다.

        Args:
            scenario_id: 시나리오 ID
            user_id: 사용자 ID (좋아요 정보 조회용, 선택적)

        Returns:
            시나리오 상세 정보 (좋아요, 댓글 정보 포함)
        """
        logger.info("get_scenario_detail", "Getting scenario detail",
                   scenario_id=scenario_id)

        # ScenarioService로 시나리오 정보 가져오기
        scenario = self.scenario_service.load_scenario(scenario_id)

        if not scenario:
            logger.warning("get_scenario_detail", "Scenario not found",
                          scenario_id=scenario_id)
            return None

        # 좋아요 개수 조회
        like_count = await self.repository.get_scenario_like_count(scenario_id)

        # 사용자 좋아요 여부 확인
        user_liked = False
        if user_id:
            user_liked = await self.repository.check_user_liked_scenario(
                scenario_id, user_id
            )

        # 댓글 개수 조회 (최상위 댓글만)
        comments = await self.repository.get_scenario_comments(
            scenario_id, limit=0
        )
        comment_count = len(comments)

        # 시나리오 정보에 추가 정보 추가
        result = {
            **scenario,
            "like_count": like_count,
            "user_liked": user_liked,
            "comment_count": comment_count
        }

        logger.info("get_scenario_detail", "Scenario detail retrieved",
                   scenario_id=scenario_id,
                   like_count=like_count,
                   comment_count=comment_count)

        return result

    async def toggle_like(
        self,
        scenario_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        시나리오 좋아요 토글

        Args:
            scenario_id: 시나리오 ID
            user_id: 사용자 ID

        Returns:
            좋아요 결과
            {
                "is_liked": bool,
                "like_count": int
            }
        """
        logger.info("toggle_like", "Toggling scenario like",
                   scenario_id=scenario_id, user_id=user_id)

        async with self.db.begin():
            # Repository로 좋아요 토글
            is_liked = await self.repository.toggle_scenario_like(
                scenario_id, user_id
            )

            # 좋아요 개수 조회
            like_count = await self.repository.get_scenario_like_count(scenario_id)

        logger.info("toggle_like", "Like toggled",
                   scenario_id=scenario_id,
                   is_liked=is_liked,
                   like_count=like_count)

        return {
            "is_liked": is_liked,
            "like_count": like_count
        }

    async def create_comment(
        self,
        scenario_id: str,
        user_id: str,
        content: str,
        parent_comment_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        댓글 작성

        Args:
            scenario_id: 시나리오 ID
            user_id: 사용자 ID
            content: 댓글 내용
            parent_comment_id: 부모 댓글 ID (대댓글인 경우)

        Returns:
            생성된 댓글 정보
        """
        logger.info("create_comment", "Creating comment",
                   scenario_id=scenario_id, user_id=user_id)

        # 댓글 내용 검증
        if not content or len(content.strip()) == 0:
            logger.warning("create_comment", "Empty comment content")
            raise ValueError("댓글 내용을 입력해주세요.")

        if len(content) > 500:
            logger.warning("create_comment", "Comment too long")
            raise ValueError("댓글은 500자 이내로 작성해주세요.")

        async with self.db.begin():
            # Repository로 댓글 생성
            comment = await self.repository.create_comment(
                scenario_id=scenario_id,
                user_id=user_id,
                content=content,
                parent_comment_id=parent_comment_id
            )

        logger.info("create_comment", "Comment created",
                   comment_id=comment.id)

        return self._comment_to_dict(comment)

    async def update_comment(
        self,
        comment_id: int,
        user_id: str,
        content: str
    ) -> Optional[Dict[str, Any]]:
        """
        댓글 수정

        Args:
            comment_id: 댓글 ID
            user_id: 사용자 ID (권한 체크용)
            content: 새 댓글 내용

        Returns:
            수정된 댓글 정보 (권한 없으면 None)
        """
        logger.info("update_comment", "Updating comment",
                   comment_id=comment_id, user_id=user_id)

        # 댓글 내용 검증
        if not content or len(content.strip()) == 0:
            logger.warning("update_comment", "Empty comment content")
            raise ValueError("댓글 내용을 입력해주세요.")

        if len(content) > 500:
            logger.warning("update_comment", "Comment too long")
            raise ValueError("댓글은 500자 이내로 작성해주세요.")

        async with self.db.begin():
            # Repository로 댓글 수정
            comment = await self.repository.update_comment(
                comment_id=comment_id,
                user_id=user_id,
                content=content
            )

        if not comment:
            logger.warning("update_comment", "Comment not found or no permission",
                          comment_id=comment_id)
            return None

        logger.info("update_comment", "Comment updated",
                   comment_id=comment_id)

        return self._comment_to_dict(comment)

    async def delete_comment(
        self,
        comment_id: int,
        user_id: str
    ) -> bool:
        """
        댓글 삭제 (소프트 삭제)

        Args:
            comment_id: 댓글 ID
            user_id: 사용자 ID (권한 체크용)

        Returns:
            삭제 성공 여부
        """
        logger.info("delete_comment", "Deleting comment",
                   comment_id=comment_id, user_id=user_id)

        async with self.db.begin():
            # Repository로 댓글 삭제
            success = await self.repository.delete_comment(
                comment_id=comment_id,
                user_id=user_id
            )

        if success:
            logger.info("delete_comment", "Comment deleted",
                       comment_id=comment_id)
        else:
            logger.warning("delete_comment", "Comment not found or no permission",
                          comment_id=comment_id)

        return success

    async def toggle_comment_like(
        self,
        comment_id: int,
        user_id: str
    ) -> Dict[str, Any]:
        """
        댓글 추천 토글

        Args:
            comment_id: 댓글 ID
            user_id: 사용자 ID

        Returns:
            추천 결과
            {
                "is_liked": bool,
                "like_count": int
            }
        """
        logger.info("toggle_comment_like", "Toggling comment like",
                   comment_id=comment_id, user_id=user_id)

        async with self.db.begin():
            # Repository로 추천 토글
            is_liked, like_count = await self.repository.toggle_comment_like(
                comment_id=comment_id,
                user_id=user_id
            )

        logger.info("toggle_comment_like", "Like toggled",
                   comment_id=comment_id,
                   is_liked=is_liked,
                   like_count=like_count)

        return {
            "is_liked": is_liked,
            "like_count": like_count
        }

    async def get_comments(
        self,
        scenario_id: str,
        sort_by: str = "created_at",
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        시나리오 댓글 목록 조회

        Args:
            scenario_id: 시나리오 ID
            sort_by: 정렬 기준 (created_at, like_count)
            limit: 페이징 크기
            offset: 페이징 오프셋

        Returns:
            댓글 리스트
        """
        logger.info("get_comments", "Getting comments",
                   scenario_id=scenario_id, sort_by=sort_by)

        # Repository로 댓글 조회
        comments = await self.repository.get_scenario_comments(
            scenario_id=scenario_id,
            sort_by=sort_by,
            limit=limit,
            offset=offset
        )

        # ORM → Dict 변환
        result = [self._comment_to_dict(c) for c in comments]

        logger.info("get_comments", f"Retrieved {len(result)} comments",
                   scenario_id=scenario_id)

        return result

    async def get_comment_replies(
        self,
        parent_comment_id: int,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        대댓글 조회

        Args:
            parent_comment_id: 부모 댓글 ID
            limit: 페이징 크기
            offset: 페이징 오프셋

        Returns:
            대댓글 리스트
        """
        logger.info("get_comment_replies", "Getting replies",
                   parent_comment_id=parent_comment_id)

        # Repository로 대댓글 조회
        replies = await self.repository.get_comment_replies(
            parent_comment_id=parent_comment_id,
            limit=limit,
            offset=offset
        )

        # ORM → Dict 변환
        result = [self._comment_to_dict(r) for r in replies]

        logger.info("get_comment_replies", f"Retrieved {len(result)} replies",
                   parent_comment_id=parent_comment_id)

        return result

    def _comment_to_dict(self, comment: ScenarioComment) -> Dict[str, Any]:
        """
        ScenarioComment ORM → Dict 변환

        Args:
            comment: ScenarioComment ORM 객체

        Returns:
            댓글 dict
        """
        return {
            "id": comment.id,
            "scenario_id": comment.scenario_id,
            "user_id": comment.user_id,
            "content": comment.content,
            "parent_comment_id": comment.parent_comment_id,
            "like_count": comment.like_count,
            "is_edited": comment.is_edited,
            "is_deleted": comment.is_deleted,
            "created_at": comment.created_at.isoformat() if comment.created_at else None,
            "updated_at": comment.updated_at.isoformat() if comment.updated_at else None
        }
