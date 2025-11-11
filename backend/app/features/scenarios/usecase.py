"""
Scenarios Feature - UseCase
시나리오 목록, 상세, 댓글, 좋아요 비즈니스 로직
Layer 2: UseCase (4-Layer Architecture)
"""
import asyncio
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
        시나리오 목록 조회 (Bulk 조회로 N+1 문제 해결)

        ScenarioService를 통해 시나리오 목록을 가져오고,
        Repository를 통해 좋아요 정보를 Bulk로 추가합니다.

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

        # 시나리오 ID 리스트 추출
        scenario_ids = [s.get("scenario_id") for s in scenarios]

        if not scenario_ids:
            logger.info("list_scenarios", "No scenarios found")
            return []

        # Bulk 조회: 좋아요 개수, 사용자 좋아요 여부, 댓글 개수 (반복문 이전에 한 번씩만 호출)
        like_counts = await self.repository.get_like_counts_for_scenarios(scenario_ids)
        user_liked_set = set()
        if user_id:
            user_liked_set = await self.repository.get_user_likes_for_scenarios(
                scenario_ids, user_id
            )
        comment_counts = await self.repository.get_comment_counts_for_scenarios(scenario_ids)

        # 각 시나리오에 통계 정보 추가 (DB 쿼리 없이 Dict/Set 조회만)
        result = []
        for scenario in scenarios:
            scenario_id = scenario.get("scenario_id")

            scenario_with_stats = {
                **scenario,
                "like_count": like_counts.get(scenario_id, 0),
                "user_liked": scenario_id in user_liked_set,
                "comment_count": comment_counts.get(scenario_id, 0)
            }
            result.append(scenario_with_stats)

        logger.info("list_scenarios", f"Retrieved {len(result)} scenarios")
        return result

    async def get_scenario_detail(
        self,
        scenario_id: str,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        시나리오 상세 조회 (asyncio.gather로 병렬 쿼리 최적화)

        ScenarioService를 통해 시나리오 상세 정보를 가져오고,
        Repository를 통해 좋아요 및 댓글 정보를 병렬로 조회합니다.

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

        # 3개의 DB 쿼리를 asyncio.gather로 병렬 실행
        if user_id:
            # 사용자가 로그인한 경우: 좋아요 수, 사용자 좋아요 여부, 댓글 수
            like_count, user_liked, comment_count = await asyncio.gather(
                self.repository.get_scenario_like_count(scenario_id),
                self.repository.check_user_liked_scenario(scenario_id, user_id),
                self.repository.get_scenario_comment_count(scenario_id)
            )
        else:
            # 비로그인 사용자: 좋아요 수, 댓글 수만 조회
            like_count, comment_count = await asyncio.gather(
                self.repository.get_scenario_like_count(scenario_id),
                self.repository.get_scenario_comment_count(scenario_id)
            )
            user_liked = False

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

    async def check_scenario_like(
        self,
        scenario_id: str,
        user_id: str
    ) -> bool:
        """
        시나리오 좋아요 상태 확인

        Args:
            scenario_id: 시나리오 ID
            user_id: 사용자 ID

        Returns:
            좋아요 여부
        """
        logger.info("check_scenario_like", "Checking scenario like status",
                   scenario_id=scenario_id, user_id=user_id)

        liked = await self.repository.check_user_liked_scenario(
            scenario_id=scenario_id,
            user_id=user_id
        )

        logger.info("check_scenario_like", f"Like status: {liked}",
                   scenario_id=scenario_id)

        return liked

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
            생성된 댓글 정보 (username, display_name 포함)
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

            # 사용자 정보 조회 (username, display_name)
            user_info = await self.repository.get_user_info(user_id)

        logger.info("create_comment", "Comment created",
                   comment_id=comment.id)

        # 댓글 정보에 사용자 정보 포함 (방금 생성한 댓글이므로 is_liked는 False)
        return {
            "id": comment.id,
            "scenario_id": comment.scenario_id,
            "user_id": str(comment.user_id),
            "username": user_info.get("username", ""),
            "display_name": user_info.get("display_name", ""),
            "content": comment.content,
            "parent_comment_id": comment.parent_comment_id,
            "like_count": comment.like_count,
            "is_liked": False,
            "is_edited": comment.is_edited,
            "is_deleted": comment.is_deleted,
            "created_at": comment.created_at.isoformat() if comment.created_at else None,
            "updated_at": comment.updated_at.isoformat() if comment.updated_at else None
        }

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

            # 사용자 정보 조회 (username, display_name)
            user_info = await self.repository.get_user_info(str(comment.user_id))

            # is_liked 조회 (현재 수정하는 사용자가 이 댓글을 좋아요 했는지)
            is_liked = False
            if user_id:
                # comment_likes 테이블에서 확인
                from .models import CommentLike
                from sqlalchemy import select, func, and_

                stmt = select(func.count(CommentLike.comment_id)).where(
                    and_(
                        CommentLike.comment_id == comment_id,
                        CommentLike.user_id == user_id
                    )
                )
                result = await self.db.execute(stmt)
                is_liked = result.scalar_one() > 0

        logger.info("update_comment", "Comment updated",
                   comment_id=comment_id)

        # 실제 데이터로 CommentResponse 반환
        return {
            "id": comment.id,
            "scenario_id": comment.scenario_id,
            "user_id": str(comment.user_id),
            "username": user_info.get("username", ""),
            "display_name": user_info.get("display_name", ""),
            "content": comment.content,
            "parent_comment_id": comment.parent_comment_id,
            "like_count": comment.like_count,
            "is_liked": is_liked,
            "is_edited": comment.is_edited,
            "is_deleted": comment.is_deleted,
            "created_at": comment.created_at.isoformat() if comment.created_at else None,
            "updated_at": comment.updated_at.isoformat() if comment.updated_at else None
        }

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
        offset: int = 0,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        시나리오 댓글 목록 조회

        Args:
            scenario_id: 시나리오 ID
            sort_by: 정렬 기준 (created_at, like_count)
            limit: 페이징 크기
            offset: 페이징 오프셋
            user_id: 사용자 ID (is_liked 조회용, 선택적)

        Returns:
            댓글 리스트 (is_liked 포함)
        """
        logger.info("get_comments", "Getting comments",
                   scenario_id=scenario_id, sort_by=sort_by)

        # Repository로 댓글 조회 (comment, username, display_name, is_liked 튜플 리스트 반환)
        comments_with_user = await self.repository.get_scenario_comments(
            scenario_id=scenario_id,
            sort_by=sort_by,
            limit=limit,
            offset=offset,
            user_id=user_id
        )

        # Tuple → Dict 변환 (username, display_name, is_liked 포함)
        result = []
        for comment, username, display_name, is_liked in comments_with_user:
            comment_dict = {
                "id": comment.id,
                "scenario_id": comment.scenario_id,
                "user_id": str(comment.user_id),
                "username": username,
                "display_name": display_name,
                "content": comment.content,
                "parent_comment_id": comment.parent_comment_id,
                "like_count": comment.like_count,
                "is_liked": is_liked,
                "is_edited": comment.is_edited,
                "is_deleted": comment.is_deleted,
                "created_at": comment.created_at.isoformat() if comment.created_at else None,
                "updated_at": comment.updated_at.isoformat() if comment.updated_at else None
            }
            result.append(comment_dict)

        logger.info("get_comments", f"Retrieved {len(result)} comments",
                   scenario_id=scenario_id)

        return result

    async def get_comment_replies(
        self,
        parent_comment_id: int,
        limit: int = 20,
        offset: int = 0,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        대댓글 조회

        Args:
            parent_comment_id: 부모 댓글 ID
            limit: 페이징 크기
            offset: 페이징 오프셋
            user_id: 사용자 ID (is_liked 조회용, 선택적)

        Returns:
            대댓글 리스트 (is_liked 포함)
        """
        logger.info("get_comment_replies", "Getting replies",
                   parent_comment_id=parent_comment_id)

        # Repository로 대댓글 조회 (comment, username, display_name, is_liked 튜플 리스트 반환)
        replies_with_user = await self.repository.get_comment_replies(
            parent_comment_id=parent_comment_id,
            limit=limit,
            offset=offset,
            user_id=user_id
        )

        # Tuple → Dict 변환 (username, display_name, is_liked 포함)
        result = []
        for reply, username, display_name, is_liked in replies_with_user:
            reply_dict = {
                "id": reply.id,
                "scenario_id": reply.scenario_id,
                "user_id": str(reply.user_id),
                "username": username,
                "display_name": display_name,
                "content": reply.content,
                "parent_comment_id": reply.parent_comment_id,
                "like_count": reply.like_count,
                "is_liked": is_liked,
                "is_edited": reply.is_edited,
                "is_deleted": reply.is_deleted,
                "created_at": reply.created_at.isoformat() if reply.created_at else None,
                "updated_at": reply.updated_at.isoformat() if reply.updated_at else None
            }
            result.append(reply_dict)

        logger.info("get_comment_replies", f"Retrieved {len(result)} replies",
                   parent_comment_id=parent_comment_id)

        return result

    async def record_scenario_view(
        self,
        scenario_id: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        시나리오 조회 기록

        Args:
            scenario_id: 시나리오 ID
            user_id: 사용자 ID (선택)
            ip_address: IP 주소 (선택)
            user_agent: User Agent (선택)

        Returns:
            성공 여부
        """
        logger.info("record_scenario_view", "Recording scenario view",
                   scenario_id=scenario_id, user_id=user_id)

        async with self.db.begin():
            success = await self.repository.record_scenario_view(
                scenario_id=scenario_id,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent
            )

        logger.info("record_scenario_view", f"View record result: {success}",
                   scenario_id=scenario_id)

        return success
