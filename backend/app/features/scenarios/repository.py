"""
Scenarios Feature - Repository
시나리오 댓글 및 좋아요 DB 접근 레이어
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete, update
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from .models import ScenarioComment, ScenarioLike, CommentLike, ScenarioView
from app.core.logging import get_repository_logger

logger = get_repository_logger("Scenario")


class ScenarioRepository:
    """
    [Layer 4] Repository
    책임: 시나리오 댓글/좋아요 CRUD
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================================
    # Comment Management
    # ============================================================

    async def get_scenario_comments(
        self,
        scenario_id: str,
        sort_by: str = "created_at",  # created_at, like_count
        limit: int = 50,
        offset: int = 0
    ) -> List[ScenarioComment]:
        """
        시나리오 댓글 목록 조회 (최상위 댓글만)

        Args:
            scenario_id: 시나리오 ID
            sort_by: 정렬 기준 (created_at, like_count)
            limit: 페이징 크기
            offset: 페이징 오프셋

        Returns:
            ScenarioComment 리스트
        """
        logger.debug("get_scenario_comments", f"Fetching comments for {scenario_id}",
                    sort_by=sort_by, limit=limit)

        stmt = (
            select(ScenarioComment)
            .where(
                and_(
                    ScenarioComment.scenario_id == scenario_id,
                    ScenarioComment.parent_comment_id.is_(None),
                    ScenarioComment.is_deleted == False
                )
            )
        )

        if sort_by == "like_count":
            stmt = stmt.order_by(ScenarioComment.like_count.desc(), ScenarioComment.created_at.desc())
        else:
            stmt = stmt.order_by(ScenarioComment.created_at.desc())

        stmt = stmt.limit(limit).offset(offset)

        result = await self.db.execute(stmt)
        comments = result.scalars().all()

        logger.debug("get_scenario_comments", f"Fetched {len(comments)} comments")
        return list(comments)

    async def get_comment_replies(
        self,
        parent_comment_id: int,
        limit: int = 20,
        offset: int = 0
    ) -> List[ScenarioComment]:
        """
        대댓글 조회

        Args:
            parent_comment_id: 부모 댓글 ID
            limit: 페이징 크기
            offset: 페이징 오프셋

        Returns:
            대댓글 리스트
        """
        logger.debug("get_comment_replies", f"Fetching replies for comment {parent_comment_id}")

        stmt = (
            select(ScenarioComment)
            .where(
                and_(
                    ScenarioComment.parent_comment_id == parent_comment_id,
                    ScenarioComment.is_deleted == False
                )
            )
            .order_by(ScenarioComment.created_at.asc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(stmt)
        replies = result.scalars().all()

        logger.debug("get_comment_replies", f"Fetched {len(replies)} replies")
        return list(replies)

    async def create_comment(
        self,
        scenario_id: str,
        user_id: str,
        content: str,
        parent_comment_id: Optional[int] = None
    ) -> ScenarioComment:
        """
        댓글 생성

        Args:
            scenario_id: 시나리오 ID
            user_id: 사용자 ID
            content: 댓글 내용
            parent_comment_id: 부모 댓글 ID (대댓글인 경우)

        Returns:
            생성된 ScenarioComment
        """
        logger.info("create_comment", f"Creating comment for scenario {scenario_id}", user_id=user_id)

        comment = ScenarioComment(
            scenario_id=scenario_id,
            user_id=user_id,
            content=content,
            parent_comment_id=parent_comment_id
        )
        self.db.add(comment)
        await self.db.flush()

        logger.info("create_comment", f"Comment created", comment_id=comment.id)
        return comment

    async def update_comment(
        self,
        comment_id: int,
        user_id: str,
        content: str
    ) -> Optional[ScenarioComment]:
        """
        댓글 수정

        Args:
            comment_id: 댓글 ID
            user_id: 사용자 ID (권한 체크용)
            content: 새 댓글 내용

        Returns:
            수정된 ScenarioComment (권한 없으면 None)
        """
        logger.info("update_comment", f"Updating comment {comment_id}", user_id=user_id)

        stmt = select(ScenarioComment).where(
            and_(
                ScenarioComment.id == comment_id,
                ScenarioComment.user_id == user_id,
                ScenarioComment.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        comment = result.scalar_one_or_none()

        if not comment:
            logger.warning("update_comment", f"Comment not found or no permission", comment_id=comment_id)
            return None

        comment.content = content
        comment.is_edited = True
        comment.updated_at = datetime.utcnow()
        await self.db.flush()

        logger.info("update_comment", f"Comment updated", comment_id=comment_id)
        return comment

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
        logger.warning("delete_comment", f"Deleting comment {comment_id}", user_id=user_id)

        stmt = select(ScenarioComment).where(
            and_(
                ScenarioComment.id == comment_id,
                ScenarioComment.user_id == user_id
            )
        )
        result = await self.db.execute(stmt)
        comment = result.scalar_one_or_none()

        if not comment:
            logger.warning("delete_comment", f"Comment not found or no permission", comment_id=comment_id)
            return False

        comment.is_deleted = True
        comment.updated_at = datetime.utcnow()
        await self.db.flush()

        logger.warning("delete_comment", f"Comment deleted", comment_id=comment_id)
        return True

    # ============================================================
    # Like Management
    # ============================================================

    async def toggle_comment_like(
        self,
        comment_id: int,
        user_id: str
    ) -> Tuple[bool, int]:
        """
        댓글 추천 토글 (추천/취소)

        Args:
            comment_id: 댓글 ID
            user_id: 사용자 ID

        Returns:
            (is_liked, new_like_count)
        """
        logger.info("toggle_comment_like", f"Toggling like for comment {comment_id}", user_id=user_id)

        # 기존 추천 확인
        stmt = select(CommentLike).where(
            and_(
                CommentLike.comment_id == comment_id,
                CommentLike.user_id == user_id
            )
        )
        result = await self.db.execute(stmt)
        existing_like = result.scalar_one_or_none()

        if existing_like:
            # 추천 취소
            await self.db.delete(existing_like)

            # 댓글 like_count 감소
            stmt = update(ScenarioComment).where(
                ScenarioComment.id == comment_id
            ).values(
                like_count=ScenarioComment.like_count - 1
            )
            await self.db.execute(stmt)
            await self.db.flush()

            # 새 like_count 조회
            stmt = select(ScenarioComment.like_count).where(ScenarioComment.id == comment_id)
            result = await self.db.execute(stmt)
            new_count = result.scalar_one()

            logger.info("toggle_comment_like", f"Like removed", comment_id=comment_id, new_count=new_count)
            return False, new_count
        else:
            # 추천 추가
            like = CommentLike(comment_id=comment_id, user_id=user_id)
            self.db.add(like)

            # 댓글 like_count 증가
            stmt = update(ScenarioComment).where(
                ScenarioComment.id == comment_id
            ).values(
                like_count=ScenarioComment.like_count + 1
            )
            await self.db.execute(stmt)
            await self.db.flush()

            # 새 like_count 조회
            stmt = select(ScenarioComment.like_count).where(ScenarioComment.id == comment_id)
            result = await self.db.execute(stmt)
            new_count = result.scalar_one()

            logger.info("toggle_comment_like", f"Like added", comment_id=comment_id, new_count=new_count)
            return True, new_count

    async def toggle_scenario_like(
        self,
        scenario_id: str,
        user_id: str
    ) -> bool:
        """
        시나리오 좋아요 토글

        Args:
            scenario_id: 시나리오 ID
            user_id: 사용자 ID

        Returns:
            is_liked (True: 좋아요 추가, False: 좋아요 취소)
        """
        logger.info("toggle_scenario_like", f"Toggling like for scenario {scenario_id}", user_id=user_id)

        # 기존 좋아요 확인
        stmt = select(ScenarioLike).where(
            and_(
                ScenarioLike.scenario_id == scenario_id,
                ScenarioLike.user_id == user_id
            )
        )
        result = await self.db.execute(stmt)
        existing_like = result.scalar_one_or_none()

        if existing_like:
            # 좋아요 취소
            await self.db.delete(existing_like)
            await self.db.flush()

            logger.info("toggle_scenario_like", f"Like removed", scenario_id=scenario_id)
            return False
        else:
            # 좋아요 추가
            like = ScenarioLike(scenario_id=scenario_id, user_id=user_id)
            self.db.add(like)
            await self.db.flush()

            logger.info("toggle_scenario_like", f"Like added", scenario_id=scenario_id)
            return True

    async def get_scenario_like_count(self, scenario_id: str) -> int:
        """
        시나리오 좋아요 개수 조회

        Args:
            scenario_id: 시나리오 ID

        Returns:
            좋아요 개수
        """
        stmt = select(func.count(ScenarioLike.like_id)).where(
            ScenarioLike.scenario_id == scenario_id
        )
        result = await self.db.execute(stmt)
        count = result.scalar_one()

        return count

    async def check_user_liked_scenario(
        self,
        scenario_id: str,
        user_id: str
    ) -> bool:
        """
        사용자가 시나리오에 좋아요를 눌렀는지 확인

        Args:
            scenario_id: 시나리오 ID
            user_id: 사용자 ID

        Returns:
            좋아요 여부
        """
        stmt = select(func.count(ScenarioLike.like_id)).where(
            and_(
                ScenarioLike.scenario_id == scenario_id,
                ScenarioLike.user_id == user_id
            )
        )
        result = await self.db.execute(stmt)
        count = result.scalar_one()

        return count > 0

    # ============================================================
    # View Management
    # ============================================================

    async def record_scenario_view(
        self,
        scenario_id: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        시나리오 조회 기록 (조회수 증가)

        Args:
            scenario_id: 시나리오 ID
            user_id: 사용자 ID (선택, 익명 가능)
            ip_address: IP 주소 (선택)
            user_agent: User Agent (선택)

        Returns:
            성공 여부
        """
        logger.info("record_scenario_view", f"Recording view for scenario {scenario_id}",
                   user_id=user_id, ip_address=ip_address)

        try:
            view = ScenarioView(
                scenario_id=scenario_id,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            self.db.add(view)
            await self.db.flush()

            logger.info("record_scenario_view", f"View recorded", scenario_id=scenario_id)
            return True
        except Exception as e:
            logger.error("record_scenario_view", f"Failed to record view: {e}", scenario_id=scenario_id)
            return False
