"""
Images Feature - Controller
이미지 매핑 API 엔드포인트
Layer 2: Controller (4-Layer Architecture)
"""
from fastapi import APIRouter, Depends, Query, status
from typing import Optional

from app.features.images.usecase import ImagesUseCase
from app.features.images.repository import ImagesRepository
from app.features.images.schemas import (
    ImageMappingCreate,
    ImageMappingUpdate,
    ImageMappingResponse,
    ImageQueryResponse
)
from app.core.db.session import get_db
from app.core.errors import NotFoundException
from app.core.logging import get_controller_logger
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/images", tags=["images"])
logger = get_controller_logger("Images")


def get_usecase(db: AsyncSession = Depends(get_db)) -> ImagesUseCase:
    """ImagesUseCase 의존성 주입"""
    repository = ImagesRepository(db)
    return ImagesUseCase(repository)


@router.post("", response_model=ImageMappingResponse, status_code=status.HTTP_201_CREATED)
async def create_image_mapping(
    data: ImageMappingCreate,
    usecase: ImagesUseCase = Depends(get_usecase)
):
    """
    이미지 매핑 생성

    Args:
        data: 이미지 매핑 데이터
        usecase: ImagesUseCase

    Returns:
        ImageMappingResponse
    """
    logger.info("create_image_mapping", f"POST /api/images - {data.image_key}")
    return await usecase.create_image_mapping(data)


@router.get("", response_model=ImageQueryResponse)
async def query_images(
    scenario_id: Optional[str] = Query(None, description="시나리오 ID"),
    mapping_category: Optional[str] = Query(None, description="카테고리 (character, bg, cutscene, stage)"),
    image_key: Optional[str] = Query(None, description="이미지 키 (LIKE 검색)"),
    limit: int = Query(100, ge=1, le=1000, description="페이징 크기"),
    offset: int = Query(0, ge=0, description="페이징 오프셋"),
    usecase: ImagesUseCase = Depends(get_usecase)
):
    """
    이미지 조회 (필터링 및 페이징)

    Args:
        scenario_id: 시나리오 ID 필터
        mapping_category: 카테고리 필터
        image_key: 이미지 키 필터
        limit: 페이징 크기
        offset: 페이징 오프셋
        usecase: ImagesUseCase

    Returns:
        ImageQueryResponse
    """
    logger.info("query_images", f"GET /api/images - category={mapping_category}")
    return await usecase.query_images(
        scenario_id=scenario_id,
        mapping_category=mapping_category,
        image_key=image_key,
        limit=limit,
        offset=offset
    )


@router.get("/by-key/{image_key}", response_model=ImageMappingResponse)
async def get_image_by_key(
    image_key: str,
    scenario_id: Optional[str] = Query(None, description="시나리오 ID (우선순위)"),
    usecase: ImagesUseCase = Depends(get_usecase)
):
    """
    이미지 키로 조회

    Args:
        image_key: 이미지 키
        scenario_id: 시나리오 ID (우선순위)
        usecase: ImagesUseCase

    Returns:
        ImageMappingResponse

    Raises:
        NotFoundException: 이미지를 찾을 수 없음
    """
    logger.info("get_image_by_key", f"GET /api/images/by-key/{image_key}")

    result = await usecase.get_image_by_key(image_key, scenario_id)
    if not result:
        raise NotFoundException(f"Image not found: {image_key}")

    return result


@router.get("/character/{character_name}", response_model=dict)
async def get_character_image(
    character_name: str,
    emotion: str = Query("normal", description="감정 상태"),
    scenario_id: Optional[str] = Query(None, description="시나리오 ID"),
    usecase: ImagesUseCase = Depends(get_usecase)
):
    """
    캐릭터 이미지 URL 조회

    Args:
        character_name: 캐릭터 이름
        emotion: 감정 상태
        scenario_id: 시나리오 ID
        usecase: ImagesUseCase

    Returns:
        {"character": str, "emotion": str, "image_url": str or None}
    """
    logger.info("get_character_image", f"GET /api/images/character/{character_name}")

    image_url = await usecase.get_character_image(
        character_name=character_name,
        emotion=emotion,
        scenario_id=scenario_id
    )

    return {
        "character": character_name,
        "emotion": emotion,
        "image_url": image_url
    }


@router.get("/background/{stage_tag}", response_model=dict)
async def get_background_image(
    stage_tag: str,
    scenario_id: Optional[str] = Query(None, description="시나리오 ID"),
    usecase: ImagesUseCase = Depends(get_usecase)
):
    """
    배경 이미지 URL 조회

    Args:
        stage_tag: 스테이지 태그
        scenario_id: 시나리오 ID
        usecase: ImagesUseCase

    Returns:
        {"stage_tag": str, "image_url": str or None}
    """
    logger.info("get_background_image", f"GET /api/images/background/{stage_tag}")

    image_url = await usecase.get_background_image(
        stage_tag=stage_tag,
        scenario_id=scenario_id
    )

    return {
        "stage_tag": stage_tag,
        "image_url": image_url
    }


@router.put("/{mapping_id}", response_model=ImageMappingResponse)
async def update_image_mapping(
    mapping_id: int,
    data: ImageMappingUpdate,
    usecase: ImagesUseCase = Depends(get_usecase)
):
    """
    이미지 매핑 수정

    Args:
        mapping_id: 매핑 ID
        data: 수정 데이터
        usecase: ImagesUseCase

    Returns:
        ImageMappingResponse

    Raises:
        NotFoundException: 매핑을 찾을 수 없음
    """
    logger.info("update_image_mapping", f"PUT /api/images/{mapping_id}")
    return await usecase.update_image_mapping(mapping_id, data)


@router.delete("/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image_mapping(
    mapping_id: int,
    usecase: ImagesUseCase = Depends(get_usecase)
):
    """
    이미지 매핑 삭제

    Args:
        mapping_id: 매핑 ID
        usecase: ImagesUseCase

    Raises:
        NotFoundException: 매핑을 찾을 수 없음
    """
    logger.info("delete_image_mapping", f"DELETE /api/images/{mapping_id}")
    await usecase.delete_image_mapping(mapping_id)
