"""
Image Management Utility
이미지 파일 관리 (업로드, 저장, 조회, 삭제)

Features:
- 이미지 파일 검증 (MIME type, 크기)
- 파일 저장 (로컬 파일 시스템)
- 썸네일 생성
- 이미지 메타데이터 추출
- 안전한 파일명 생성
"""
import os
import uuid
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from app.core.config import get_settings
from app.core.logging import get_parent_logger

settings = get_settings()
logger = get_parent_logger("ImageManager")

# 허용된 이미지 확장자
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}

# 최대 파일 크기 (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


class ImageManager:
    """
    이미지 파일 관리 시스템

    Features:
    - 파일 업로드 및 검증
    - 안전한 파일명 생성
    - 썸네일 생성 (PIL 사용)
    - 메타데이터 추출

    Example:
        manager = ImageManager(upload_dir="/app/uploads/images")

        # 파일 저장
        file_info = manager.save_image(
            file_content=image_bytes,
            filename="profile.jpg",
            user_id="user123"
        )

        # 썸네일 생성
        thumbnail_path = manager.create_thumbnail(
            file_info["file_path"],
            size=(200, 200)
        )
    """

    def __init__(self, upload_dir: Optional[Path] = None):
        """
        Args:
            upload_dir: 업로드 디렉토리 경로 (None이면 기본값 사용)
        """
        if upload_dir is None:
            # 기본 업로드 디렉토리: backend/uploads/images
            self.upload_dir = Path(__file__).parent.parent.parent.parent / "uploads" / "images"
        else:
            self.upload_dir = upload_dir

        # 디렉토리 생성
        self.upload_dir.mkdir(parents=True, exist_ok=True)

        if not PIL_AVAILABLE:
            logger.warning("__init__", "Pillow not available, thumbnail generation disabled")

        logger.info("__init__", "ImageManager initialized", upload_dir=str(self.upload_dir))

    def validate_image(self, file_content: bytes, filename: str) -> Tuple[bool, Optional[str]]:
        """
        이미지 파일 검증

        Args:
            file_content: 파일 바이너리 데이터
            filename: 파일명

        Returns:
            (is_valid, error_message)
        """
        # 1. 파일 크기 검증
        if len(file_content) > MAX_FILE_SIZE:
            return False, f"File size exceeds maximum ({MAX_FILE_SIZE / 1024 / 1024}MB)"

        # 2. 확장자 검증
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"File extension {ext} not allowed. Allowed: {ALLOWED_EXTENSIONS}"

        # 3. 이미지 파일 실제 검증 (PIL 사용)
        if PIL_AVAILABLE:
            try:
                from io import BytesIO
                img = Image.open(BytesIO(file_content))
                img.verify()  # 이미지 파일 유효성 검사
            except Exception as e:
                return False, f"Invalid image file: {e}"

        return True, None

    def generate_safe_filename(self, original_filename: str, user_id: Optional[str] = None) -> str:
        """
        안전한 파일명 생성 (UUID + 원본 확장자)

        Args:
            original_filename: 원본 파일명
            user_id: 사용자 ID (선택)

        Returns:
            안전한 파일명 (예: "user123_a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg")
        """
        ext = Path(original_filename).suffix.lower()
        unique_id = uuid.uuid4()

        if user_id:
            return f"{user_id}_{unique_id}{ext}"
        else:
            return f"{unique_id}{ext}"

    def save_image(
        self,
        file_content: bytes,
        filename: str,
        user_id: Optional[str] = None,
        subdirectory: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        이미지 파일 저장

        Args:
            file_content: 파일 바이너리 데이터
            filename: 원본 파일명
            user_id: 사용자 ID (선택)
            subdirectory: 하위 디렉토리 (예: "profiles", "scenarios")

        Returns:
            파일 정보 dict
            {
                "file_id": str,
                "file_path": str,
                "filename": str,
                "original_filename": str,
                "size": int,
                "uploaded_at": str
            }
        """
        # 검증
        is_valid, error_msg = self.validate_image(file_content, filename)
        if not is_valid:
            raise ValueError(f"Image validation failed: {error_msg}")

        # 안전한 파일명 생성
        safe_filename = self.generate_safe_filename(filename, user_id)

        # 저장 경로 결정
        if subdirectory:
            save_dir = self.upload_dir / subdirectory
            save_dir.mkdir(parents=True, exist_ok=True)
        else:
            save_dir = self.upload_dir

        file_path = save_dir / safe_filename

        # 파일 저장
        try:
            with open(file_path, 'wb') as f:
                f.write(file_content)

            logger.info("save_image", "Image saved",
                       filename=safe_filename,
                       size=len(file_content))

            # 파일 ID (SHA256 해시)
            file_hash = hashlib.sha256(file_content).hexdigest()[:16]

            return {
                "file_id": file_hash,
                "file_path": str(file_path),
                "filename": safe_filename,
                "original_filename": filename,
                "size": len(file_content),
                "uploaded_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error("save_image", f"Failed to save image: {e}")
            raise

    def get_image_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        이미지 메타데이터 추출

        Args:
            file_path: 이미지 파일 경로

        Returns:
            메타데이터 dict
        """
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Image not found: {file_path}")

        metadata = {
            "file_path": file_path,
            "file_size": Path(file_path).stat().st_size,
            "extension": Path(file_path).suffix
        }

        if PIL_AVAILABLE:
            try:
                img = Image.open(file_path)
                metadata.update({
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "mode": img.mode
                })
            except Exception as e:
                logger.warning("get_image_metadata", f"Failed to extract metadata: {e}")

        return metadata

    def create_thumbnail(
        self,
        image_path: str,
        size: Tuple[int, int] = (200, 200),
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        썸네일 생성

        Args:
            image_path: 원본 이미지 경로
            size: 썸네일 크기 (width, height)
            output_path: 출력 경로 (None이면 자동 생성)

        Returns:
            썸네일 파일 경로 또는 None (실패 시)
        """
        if not PIL_AVAILABLE:
            logger.warning("create_thumbnail", "PIL not available")
            return None

        if not Path(image_path).exists():
            logger.error("create_thumbnail", f"Image not found: {image_path}")
            return None

        try:
            img = Image.open(image_path)

            # 비율 유지하며 리사이즈
            img.thumbnail(size, Image.Resampling.LANCZOS)

            # 출력 경로 결정
            if output_path is None:
                path = Path(image_path)
                output_path = str(path.parent / f"{path.stem}_thumb{path.suffix}")

            # 썸네일 저장
            img.save(output_path)

            logger.info("create_thumbnail", "Thumbnail created",
                       original=image_path,
                       thumbnail=output_path,
                       size=size)

            return output_path

        except Exception as e:
            logger.error("create_thumbnail", f"Failed to create thumbnail: {e}")
            return None

    def delete_image(self, file_path: str) -> bool:
        """
        이미지 삭제

        Args:
            file_path: 삭제할 이미지 경로

        Returns:
            삭제 성공 여부
        """
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.info("delete_image", f"Image deleted: {file_path}")
                return True
            else:
                logger.warning("delete_image", f"Image not found: {file_path}")
                return False

        except Exception as e:
            logger.error("delete_image", f"Failed to delete image: {e}")
            return False

    def list_images(self, subdirectory: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        이미지 목록 조회

        Args:
            subdirectory: 하위 디렉토리 (None이면 전체)

        Returns:
            이미지 정보 리스트
        """
        if subdirectory:
            search_dir = self.upload_dir / subdirectory
        else:
            search_dir = self.upload_dir

        if not search_dir.exists():
            return []

        images = []
        for ext in ALLOWED_EXTENSIONS:
            for file_path in search_dir.glob(f"*{ext}"):
                try:
                    metadata = self.get_image_metadata(str(file_path))
                    images.append(metadata)
                except Exception as e:
                    logger.warning("list_images", f"Failed to get metadata for {file_path}: {e}")

        logger.info("list_images", f"Found {len(images)} images", directory=str(search_dir))
        return images
