"""
============================================================
🖼️ Gallery API Router
============================================================
사용자 이미지 갤러리 관리 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Dict
import logging

from src.auth.dependencies import require_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gallery", tags=["gallery"])

# ============================================================
# Database Manager Dependency
# ============================================================
db_manager = None


def set_db_manager(manager):
    """DB Manager를 설정합니다"""
    global db_manager
    db_manager = manager


@router.get("/my-images")
async def get_my_unlocked_images(
    scenario_id: Optional[str] = Query(None, description="시나리오 ID (전체 조회 시 생략)"),
    user: Dict = Depends(require_auth)
):
    """
    내가 획득한 이미지 목록 조회

    - 획득한 이미지만 반환
    - scenario_id 생략 시 전체 시나리오의 획득 이미지 반환
    """
    try:
        user_id = user["user_id"]
        images = db_manager.get_user_unlocked_images(user_id, scenario_id)

        return {
            "success": True,
            "count": len(images),
            "images": images
        }

    except Exception as e:
        logger.error(f"Failed to get unlocked images for user {user.get('user_id')}: {e}")
        raise HTTPException(status_code=500, detail="이미지 조회 실패")


@router.get("/all-images")
async def get_all_images_with_status(
    scenario_id: Optional[str] = Query(None, description="시나리오 ID (전체 조회 시 생략)"),
    user: Dict = Depends(require_auth)
):
    """
    모든 이미지 + 획득 상태 조회

    - 모든 이미지 반환 (획득/미획득 구분)
    - is_unlocked 필드로 획득 여부 확인 가능
    """
    try:
        user_id = user["user_id"]
        images = db_manager.get_all_images_with_unlock_status(user_id, scenario_id)

        # 획득/미획득 분리
        unlocked = [img for img in images if img.get("is_unlocked")]
        locked = [img for img in images if not img.get("is_unlocked")]

        return {
            "success": True,
            "total": len(images),
            "unlocked_count": len(unlocked),
            "locked_count": len(locked),
            "unlocked_images": unlocked,
            "locked_images": locked,
            "all_images": images  # 전체 목록도 제공
        }

    except Exception as e:
        logger.error(f"Failed to get all images for user {user.get('user_id')}: {e}")
        raise HTTPException(status_code=500, detail="이미지 조회 실패")


@router.get("/stats")
async def get_gallery_stats(
    scenario_id: Optional[str] = Query(None, description="시나리오 ID (전체 조회 시 생략)"),
    user: Dict = Depends(require_auth)
):
    """
    갤러리 통계 조회

    - 전체 이미지 수
    - 획득한 이미지 수
    - 획득률 (%)
    """
    try:
        user_id = user["user_id"]
        stats = db_manager.get_user_gallery_stats(user_id, scenario_id)

        if not stats:
            return {
                "success": True,
                "total_images": 0,
                "unlocked_images": 0,
                "unlock_percentage": 0.0
            }

        return {
            "success": True,
            **stats
        }

    except Exception as e:
        logger.error(f"Failed to get gallery stats for user {user.get('user_id')}: {e}")
        raise HTTPException(status_code=500, detail="통계 조회 실패")


@router.post("/unlock/{image_id}")
async def unlock_image_manual(
    image_id: str,
    user: Dict = Depends(require_auth)
):
    """
    이미지 수동 획득 (관리자/테스트용)

    - 특정 이미지를 수동으로 획득 처리
    """
    try:
        user_id = user["user_id"]
        newly_unlocked = db_manager.unlock_image_for_user(
            user_id=user_id,
            image_id=image_id,
            unlock_method="manual"
        )

        return {
            "success": True,
            "newly_unlocked": newly_unlocked,
            "message": "새로 획득했습니다" if newly_unlocked else "이미 획득한 이미지입니다"
        }

    except Exception as e:
        logger.error(f"Failed to unlock image {image_id} for user {user.get('user_id')}: {e}")
        raise HTTPException(status_code=500, detail="이미지 획득 처리 실패")
