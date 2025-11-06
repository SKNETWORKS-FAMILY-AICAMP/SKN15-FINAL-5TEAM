"""
시스템 엔드포인트
- 서버 상태 확인
- 헬스 체크 (ALB용)
"""

from fastapi import APIRouter, Depends
from src.api.models import MessageResponse
from src.api.dependencies import get_db_manager, get_cache_manager
from src.infrastructure.database.db_manager import DatabaseManager

router = APIRouter()


@router.get("/", response_model=MessageResponse, tags=["System"])
async def root():
    """
    서버 상태 확인

    Returns:
        서버 실행 상태 및 버전 정보
    """
    return {
        "message": "KIME Chat API is running",
        "status": "running",
        "service": "KIME Chat API",
        "version": "2.0.0"
    }


@router.get("/health", tags=["System"])
async def health_check(
    db: DatabaseManager = Depends(get_db_manager)
):
    """
    ALB 헬스 체크 엔드포인트

    DB 연결 상태도 함께 확인

    Returns:
        헬스 체크 결과
    """
    try:
        # DB 연결 확인 (간단한 쿼리)
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy",
        "database": db_status,
        "service": "KIME Chat API"
    }


@router.get("/ping", tags=["System"])
async def ping():
    """
    간단한 핑 엔드포인트 (응답 속도 테스트용)

    Returns:
        pong
    """
    return {"message": "pong"}
