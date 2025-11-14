"""
Scenarios Feature - Repository
시나리오 댓글 및 좋아요 DB 접근 레이어
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete, update, case, literal
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from .models import (
    ScenarioComment, ScenarioLike, CommentLike, ScenarioView,
    ScenarioStage, ScenarioMicroBeat, ScenarioMission,
    ScenarioRouter, ScenarioIntentMapping
)
from app.features.auth.models import User
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
        offset: int = 0,
        user_id: Optional[str] = None
    ) -> List[Tuple[ScenarioComment, str, str, bool]]:
        """
        시나리오 댓글 목록 조회 (최상위 댓글만)
        OUTER JOIN 방식으로 is_liked 계산

        Args:
            scenario_id: 시나리오 ID
            sort_by: 정렬 기준 (created_at, like_count)
            limit: 페이징 크기
            offset: 페이징 오프셋
            user_id: 사용자 ID (is_liked 조회용, 선택적)

        Returns:
            List[Tuple[ScenarioComment, username, display_name, is_liked]]
        """
        logger.debug("get_scenario_comments", f"Fetching comments for {scenario_id}",
                    sort_by=sort_by, limit=limit)

        # is_liked 계산: OUTER JOIN 방식 사용
        # user_id가 있으면 CommentLike와 LEFT JOIN하여 is_liked 계산
        if user_id:
            # OUTER JOIN으로 CommentLike 테이블 조인
            is_liked_expr = case(
                (CommentLike.comment_id.isnot(None), True),
                else_=False
            ).label("is_liked")

            stmt = (
                select(
                    ScenarioComment,
                    User.username,
                    User.display_name,
                    is_liked_expr
                )
                .join(User, ScenarioComment.user_id == User.user_id)
                .outerjoin(
                    CommentLike,
                    and_(
                        CommentLike.comment_id == ScenarioComment.id,
                        CommentLike.user_id == user_id
                    )
                )
                .where(
                    and_(
                        ScenarioComment.scenario_id == scenario_id,
                        ScenarioComment.parent_comment_id.is_(None),
                        ScenarioComment.is_deleted == False
                    )
                )
            )
        else:
            # user_id가 없으면 is_liked는 항상 False
            stmt = (
                select(
                    ScenarioComment,
                    User.username,
                    User.display_name,
                    literal(False).label("is_liked")
                )
                .join(User, ScenarioComment.user_id == User.user_id)
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
        comments = result.all()

        logger.debug("get_scenario_comments", f"Fetched {len(comments)} comments")
        return comments

    async def get_comment_replies(
        self,
        parent_comment_id: int,
        limit: int = 20,
        offset: int = 0,
        user_id: Optional[str] = None
    ) -> List[Tuple[ScenarioComment, str, str, bool]]:
        """
        대댓글 조회
        OUTER JOIN 방식으로 is_liked 계산

        Args:
            parent_comment_id: 부모 댓글 ID
            limit: 페이징 크기
            offset: 페이징 오프셋
            user_id: 사용자 ID (is_liked 조회용, 선택적)

        Returns:
            List[Tuple[ScenarioComment, username, display_name, is_liked]]
        """
        logger.debug("get_comment_replies", f"Fetching replies for comment {parent_comment_id}")

        # is_liked 계산: OUTER JOIN 방식 사용
        if user_id:
            # OUTER JOIN으로 CommentLike 테이블 조인
            is_liked_expr = case(
                (CommentLike.comment_id.isnot(None), True),
                else_=False
            ).label("is_liked")

            stmt = (
                select(
                    ScenarioComment,
                    User.username,
                    User.display_name,
                    is_liked_expr
                )
                .join(User, ScenarioComment.user_id == User.user_id)
                .outerjoin(
                    CommentLike,
                    and_(
                        CommentLike.comment_id == ScenarioComment.id,
                        CommentLike.user_id == user_id
                    )
                )
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
        else:
            # user_id가 없으면 is_liked는 항상 False
            stmt = (
                select(
                    ScenarioComment,
                    User.username,
                    User.display_name,
                    literal(False).label("is_liked")
                )
                .join(User, ScenarioComment.user_id == User.user_id)
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
        replies = result.all()

        logger.debug("get_comment_replies", f"Fetched {len(replies)} replies")
        return replies

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

    async def get_user_info(self, user_id: str) -> Dict[str, str]:
        """
        사용자 정보 조회 (username, display_name)

        Args:
            user_id: 사용자 ID

        Returns:
            {"username": str, "display_name": str}
        """
        stmt = select(User.username, User.display_name).where(User.user_id == user_id)
        result = await self.db.execute(stmt)
        user_info = result.first()

        if user_info:
            return {
                "username": user_info[0],
                "display_name": user_info[1]
            }
        return {"username": "", "display_name": ""}

    # ============================================================
    # Bulk Query Methods (N+1 문제 해결)
    # ============================================================

    async def get_like_counts_for_scenarios(
        self,
        scenario_ids: List[str]
    ) -> Dict[str, int]:
        """
        여러 시나리오의 좋아요 개수를 한 번의 쿼리로 조회

        Args:
            scenario_ids: 시나리오 ID 리스트

        Returns:
            {scenario_id: like_count} 딕셔너리
        """
        if not scenario_ids:
            return {}

        stmt = (
            select(ScenarioLike.scenario_id, func.count(ScenarioLike.like_id).label("count"))
            .where(ScenarioLike.scenario_id.in_(scenario_ids))
            .group_by(ScenarioLike.scenario_id)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return {row[0]: row[1] for row in rows}

    async def get_user_likes_for_scenarios(
        self,
        scenario_ids: List[str],
        user_id: str
    ) -> set:
        """
        사용자가 좋아요한 시나리오 ID 목록을 한 번의 쿼리로 조회

        Args:
            scenario_ids: 시나리오 ID 리스트
            user_id: 사용자 ID

        Returns:
            사용자가 좋아요한 scenario_id의 Set
        """
        if not scenario_ids:
            return set()

        stmt = (
            select(ScenarioLike.scenario_id)
            .where(
                and_(
                    ScenarioLike.scenario_id.in_(scenario_ids),
                    ScenarioLike.user_id == user_id
                )
            )
        )

        result = await self.db.execute(stmt)
        rows = result.scalars().all()

        return set(rows)

    async def get_comment_counts_for_scenarios(
        self,
        scenario_ids: List[str]
    ) -> Dict[str, int]:
        """
        여러 시나리오의 댓글 개수를 한 번의 쿼리로 조회 (최상위 댓글만)

        Args:
            scenario_ids: 시나리오 ID 리스트

        Returns:
            {scenario_id: comment_count} 딕셔너리
        """
        if not scenario_ids:
            return {}

        stmt = (
            select(ScenarioComment.scenario_id, func.count(ScenarioComment.id).label("count"))
            .where(
                and_(
                    ScenarioComment.scenario_id.in_(scenario_ids),
                    ScenarioComment.parent_comment_id.is_(None),
                    ScenarioComment.is_deleted == False
                )
            )
            .group_by(ScenarioComment.scenario_id)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return {row[0]: row[1] for row in rows}

    async def get_scenario_statistics(
        self,
        scenario_id: str,
        user_id: Optional[str] = None
    ) -> Tuple[int, bool, int]:
        """
        시나리오 통계를 단일 메서드로 조회 (like_count, user_liked, comment_count)

        Args:
            scenario_id: 시나리오 ID
            user_id: 사용자 ID (선택)

        Returns:
            (like_count, user_liked, comment_count) 튜플
        """
        # 좋아요 개수 조회
        like_count_stmt = select(func.count(ScenarioLike.like_id)).where(
            ScenarioLike.scenario_id == scenario_id
        )
        like_count_result = await self.db.execute(like_count_stmt)
        like_count = like_count_result.scalar_one()

        # 사용자 좋아요 여부 확인
        user_liked = False
        if user_id:
            user_liked_stmt = select(func.count(ScenarioLike.like_id)).where(
                and_(
                    ScenarioLike.scenario_id == scenario_id,
                    ScenarioLike.user_id == user_id
                )
            )
            user_liked_result = await self.db.execute(user_liked_stmt)
            user_liked = user_liked_result.scalar_one() > 0

        # 댓글 개수 조회 (최상위 댓글만)
        comment_count_stmt = select(func.count(ScenarioComment.id)).where(
            and_(
                ScenarioComment.scenario_id == scenario_id,
                ScenarioComment.parent_comment_id.is_(None),
                ScenarioComment.is_deleted == False
            )
        )
        comment_count_result = await self.db.execute(comment_count_stmt)
        comment_count = comment_count_result.scalar_one()

        return (like_count, user_liked, comment_count)

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

    async def get_scenario_comment_count(self, scenario_id: str) -> int:
        """
        시나리오 댓글 개수 조회 (최상위 댓글만)

        Args:
            scenario_id: 시나리오 ID

        Returns:
            댓글 개수
        """
        stmt = select(func.count(ScenarioComment.id)).where(
            and_(
                ScenarioComment.scenario_id == scenario_id,
                ScenarioComment.parent_comment_id.is_(None),
                ScenarioComment.is_deleted == False
            )
        )
        result = await self.db.execute(stmt)
        count = result.scalar_one()

        return count

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

    # ============================================================
    # Stage Management (Advanced Scenario System)
    # ============================================================

    async def get_scenario_stages(
        self,
        scenario_id: str,
        stage_type: Optional[str] = None
    ) -> List[ScenarioStage]:
        """
        시나리오 스테이지 목록 조회

        Args:
            scenario_id: 시나리오 ID
            stage_type: 스테이지 타입 필터 (선택)

        Returns:
            스테이지 목록
        """
        query = select(ScenarioStage).where(ScenarioStage.scenario_id == scenario_id)

        if stage_type:
            query = query.where(ScenarioStage.stage_type == stage_type)

        query = query.order_by(ScenarioStage.stage_order)

        result = await self.db.execute(query)
        stages = result.scalars().all()

        logger.debug("get_scenario_stages", f"Found {len(stages)} stages for scenario {scenario_id}")
        return list(stages)

    async def get_stage_by_id(self, stage_id: str) -> Optional[ScenarioStage]:
        """
        스테이지 ID로 조회

        Args:
            stage_id: 스테이지 ID

        Returns:
            스테이지 객체 또는 None
        """
        query = select(ScenarioStage).where(ScenarioStage.stage_id == stage_id)
        result = await self.db.execute(query)
        stage = result.scalar_one_or_none()

        if stage:
            logger.debug("get_stage_by_id", f"Stage found: {stage_id}")
        else:
            logger.debug("get_stage_by_id", f"Stage not found: {stage_id}")

        return stage

    async def create_stage(
        self,
        stage_id: str,
        scenario_id: str,
        stage_order: int,
        stage_type: str,
        config: Dict[str, Any],
        title: Optional[str] = None,
        description: Optional[str] = None
    ) -> ScenarioStage:
        """
        스테이지 생성

        Args:
            stage_id: 스테이지 ID
            scenario_id: 시나리오 ID
            stage_order: 스테이지 순서
            stage_type: 스테이지 타입
            config: 설정 (JSONB)
            title: 제목 (선택)
            description: 설명 (선택)

        Returns:
            생성된 스테이지
        """
        stage = ScenarioStage(
            stage_id=stage_id,
            scenario_id=scenario_id,
            stage_order=stage_order,
            stage_type=stage_type,
            config=config,
            title=title,
            description=description
        )

        self.db.add(stage)
        await self.db.flush()

        logger.info("create_stage", f"Stage created: {stage_id} (type: {stage_type})")
        return stage

    async def get_stage_micro_beats(self, stage_id: str) -> List[ScenarioMicroBeat]:
        """
        스테이지의 마이크로 비트 목록 조회 (scene 타입 전용)

        Args:
            stage_id: 스테이지 ID

        Returns:
            마이크로 비트 목록
        """
        query = select(ScenarioMicroBeat).where(
            ScenarioMicroBeat.stage_id == stage_id
        ).order_by(ScenarioMicroBeat.beat_order)

        result = await self.db.execute(query)
        beats = result.scalars().all()

        logger.debug("get_stage_micro_beats", f"Found {len(beats)} micro beats for stage {stage_id}")
        return list(beats)

    async def create_micro_beat(
        self,
        beat_id: str,
        stage_id: str,
        beat_order: int,
        goal: str,
        speaker_hint: Optional[List[str]] = None,
        fx: Optional[str] = None,
        i18n_key: Optional[str] = None
    ) -> ScenarioMicroBeat:
        """
        마이크로 비트 생성

        Args:
            beat_id: 비트 ID
            stage_id: 스테이지 ID
            beat_order: 비트 순서
            goal: 목표/내용
            speaker_hint: 발화자 힌트
            fx: 효과음 힌트
            i18n_key: I18N 키

        Returns:
            생성된 마이크로 비트
        """
        beat = ScenarioMicroBeat(
            beat_id=beat_id,
            stage_id=stage_id,
            beat_order=beat_order,
            goal=goal,
            speaker_hint=speaker_hint,
            fx=fx,
            i18n_key=i18n_key
        )

        self.db.add(beat)
        await self.db.flush()

        logger.info("create_micro_beat", f"Micro beat created: {beat_id}")
        return beat

    async def get_stage_mission(self, stage_id: str) -> Optional[ScenarioMission]:
        """
        스테이지의 미션 정보 조회 (mission 타입 전용)

        Args:
            stage_id: 스테이지 ID

        Returns:
            미션 정보 또는 None
        """
        query = select(ScenarioMission).where(ScenarioMission.stage_id == stage_id)
        result = await self.db.execute(query)
        mission = result.scalar_one_or_none()

        if mission:
            logger.debug("get_stage_mission", f"Mission found for stage {stage_id}")
        else:
            logger.debug("get_stage_mission", f"Mission not found for stage {stage_id}")

        return mission

    async def get_stage_router(self, stage_id: str) -> Optional[ScenarioRouter]:
        """
        스테이지의 라우터 정보 조회 (router 타입 전용)

        Args:
            stage_id: 스테이지 ID

        Returns:
            라우터 정보 또는 None
        """
        query = select(ScenarioRouter).where(ScenarioRouter.stage_id == stage_id)
        result = await self.db.execute(query)
        router = result.scalar_one_or_none()

        if router:
            logger.debug("get_stage_router", f"Router found for stage {stage_id}")
        else:
            logger.debug("get_stage_router", f"Router not found for stage {stage_id}")

        return router

    async def get_stage_intent_mappings(self, stage_id: str) -> List[ScenarioIntentMapping]:
        """
        스테이지의 인텐트 매핑 목록 조회 (free_intent 타입 전용)

        Args:
            stage_id: 스테이지 ID

        Returns:
            인텐트 매핑 목록
        """
        query = select(ScenarioIntentMapping).where(
            ScenarioIntentMapping.stage_id == stage_id
        ).order_by(ScenarioIntentMapping.priority.desc())

        result = await self.db.execute(query)
        mappings = result.scalars().all()

        logger.debug("get_stage_intent_mappings", f"Found {len(mappings)} intent mappings for stage {stage_id}")
        return list(mappings)
