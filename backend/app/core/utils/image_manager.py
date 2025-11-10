"""
[Core/Utils] 이미지 관리 유틸리티

이 모듈은 이미지 파일의 저장, 검증, 썸네일 생성, 삭제 등 전반적인 관리
기능을 제공하는 `ImageManager` 클래스를 포함합니다.
로컬 파일 시스템에 이미지를 저장하는 로직을 캡슐화합니다.

주요 기능:
- 이미지 파일 검증 (파일 형식, 크기)
- 안전한 파일명 생성 (UUID 기반)
- 로컬 파일 시스템에 파일 저장
- 썸네일 생성 (Pillow 라이브러리 필요)
- 이미지 메타데이터(크기, 포맷 등) 추출

NOTE: 썸네일 생성 등 모든 기능을 사용하려면 `requirements.txt`에 명시된
      `Pillow` 라이브러리가 설치되어 있어야 합니다.
"""
import os
import uuid
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from io import BytesIO

# Pillow 라이브러리 임포트 시도 및 사용 가능 여부 확인
try:
    from PIL import Image, ImageFile
    PIL_AVAILABLE = True
    ImageFile.LOAD_TRUNCATED_IMAGES = True # 잘린 이미지 파일도 로드 시도
except ImportError:
    PIL_AVAILABLE = False

from app.core.config import get_settings
from app.core.logging import get_parent_logger

settings = get_settings()
logger = get_parent_logger("ImageManager")

# --- 상수 정의 ---
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


# ============================================================
# 이미지 관리자 클래스
# ============================================================
class ImageManager:
    """
    로컬 파일 시스템의 이미지 파일을 관리하는 클래스입니다.
    """

    def __init__(self, upload_dir: Optional[Path] = None):
        """
        ImageManager를 초기화합니다.

        Args:
            upload_dir (Optional[Path]): 이미지를 업로드할 기본 디렉토리.
                                         None이면 프로젝트 루트의 'uploads/images'를 사용합니다.
        """
        if upload_dir is None:
            # __file__은 현재 파일의 경로. parent를 여러 번 사용하여 상위 디렉토리로 이동.
            # backend/app/core/utils -> backend/app/core -> backend/app -> backend -> project_root
            self.upload_dir = Path(__file__).parent.parent.parent.parent / "uploads" / "images"
        else:
            self.upload_dir = Path(upload_dir)

        self.upload_dir.mkdir(parents=True, exist_ok=True)

        if not PIL_AVAILABLE:
            logger.warning("__init__", "Pillow library not found. Thumbnail and validation features are disabled.")
        logger.info("__init__", "ImageManager initialized", upload_dir=str(self.upload_dir))

    def validate_image(self, file_content: bytes, filename: str) -> Tuple[bool, Optional[str]]:
        """
        업로드된 이미지 파일의 유효성을 검사합니다. (파일 크기, 확장자, 실제 이미지 형식)

        Returns:
            Tuple[bool, Optional[str]]: (유효성 여부, 실패 시 에러 메시지)
        """
        if len(file_content) > MAX_FILE_SIZE:
            return False, f"File size exceeds {MAX_FILE_SIZE // 1024 // 1024}MB"

        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"File extension '{ext}' is not allowed."

        if PIL_AVAILABLE:
            try:
                with Image.open(BytesIO(file_content)) as img:
                    img.verify()  # 이미지 데이터가 손상되지 않았는지 확인
            except Exception as e:
                return False, f"Invalid or corrupted image file: {e}"

        return True, None

    def generate_safe_filename(self, original_filename: str, user_id: Optional[str] = None) -> str:
        """
        파일 충돌 및 보안 문제를 방지하기 위해 고유하고 안전한 파일명을 생성합니다.
        (예: "user123_a1b2c3d4-e5f6-7890-abcd-ef1234567890.jpg")
        """
        ext = Path(original_filename).suffix.lower()
        unique_id = uuid.uuid4()
        return f"{user_id}_{unique_id}{ext}" if user_id else f"{unique_id}{ext}"

    def save_image(
        self,
        file_content: bytes,
        filename: str,
        user_id: Optional[str] = None,
        subdirectory: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        검증 후 이미지 파일을 로컬 파일 시스템에 저장합니다.

        Args:
            file_content (bytes): 이미지의 바이너리 데이터.
            filename (str): 사용자가 업로드한 원본 파일명.
            user_id (Optional[str]): 업로드한 사용자 ID (파일명 생성에 사용).
            subdirectory (Optional[str]): 기본 업로드 디렉토리 내의 하위 디렉토리 (예: "profiles").

        Returns:
            Dict[str, Any]: 저장된 파일의 정보를 담은 딕셔너리.
        """
        is_valid, error_msg = self.validate_image(file_content, filename)
        if not is_valid:
            raise ValueError(f"Image validation failed: {error_msg}")

        safe_filename = self.generate_safe_filename(filename, user_id)
        save_dir = self.upload_dir / subdirectory if subdirectory else self.upload_dir
        save_dir.mkdir(parents=True, exist_ok=True)
        file_path = save_dir / safe_filename

        try:
            with open(file_path, 'wb') as f:
                f.write(file_content)

            logger.info("save_image", "Image saved successfully", path=str(file_path), size_kb=len(file_content)/1024)
            
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
            logger.error("save_image", f"Failed to save image: {e}", path=str(file_path))
            raise

    def get_image_metadata(self, file_path: str) -> Dict[str, Any]:
        """Pillow를 사용하여 이미지의 메타데이터(크기, 포맷 등)를 추출합니다."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found at {file_path}")

        metadata = {"file_path": str(path), "file_size": path.stat().st_size, "extension": path.suffix}
        if PIL_AVAILABLE:
            try:
                with Image.open(path) as img:
                    metadata.update({"width": img.width, "height": img.height, "format": img.format, "mode": img.mode})
            except Exception as e:
                logger.warning("get_image_metadata", f"Could not read image metadata: {e}", path=str(path))
        return metadata

    def create_thumbnail(
        self,
        image_path: str,
        size: Tuple[int, int] = (200, 200),
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        주어진 이미지의 썸네일을 생성합니다. 원본 이미지의 비율은 유지됩니다.

        Args:
            image_path (str): 원본 이미지 파일 경로.
            size (Tuple[int, int]): 생성할 썸네일의 최대 너비와 높이.
            output_path (Optional[str]): 썸네일을 저장할 경로. None이면 원본 옆에 자동 생성.

        Returns:
            Optional[str]: 생성된 썸네일 파일의 경로. 실패 시 None.
        """
        if not PIL_AVAILABLE:
            logger.warning("create_thumbnail", "Cannot create thumbnail, Pillow library not available.")
            return None
        
        path = Path(image_path)
        if not path.exists():
            logger.error("create_thumbnail", f"Source image not found: {image_path}")
            return None

        try:
            with Image.open(path) as img:
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                if output_path is None:
                    output_path = str(path.parent / f"{path.stem}_thumb{path.suffix}")
                
                img.save(output_path)
                logger.info("create_thumbnail", "Thumbnail created successfully", output=output_path)
                return output_path
        except Exception as e:
            logger.error("create_thumbnail", f"Failed to create thumbnail: {e}", path=image_path)
            return None

    def delete_image(self, file_path: str) -> bool:
        """로컬 파일 시스템에서 이미지 파일을 삭제합니다."""
        try:
            path = Path(file_path)
            if path.is_file():
                path.unlink()
                logger.info("delete_image", f"Image deleted: {file_path}")
                return True
            logger.warning("delete_image", f"Image to delete not found: {file_path}")
            return False
        except Exception as e:
            logger.error("delete_image", f"Error deleting image: {e}", path=file_path)
            return False

    def list_images(self, subdirectory: Optional[str] = None) -> List[Dict[str, Any]]:
        """지정된 디렉토리의 모든 이미지 파일 목록과 메타데이터를 반환합니다."""
        search_dir = self.upload_dir / subdirectory if subdirectory else self.upload_dir
        if not search_dir.exists():
            return []

        images = []
        for path in search_dir.iterdir():
            if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS:
                try:
                    images.append(self.get_image_metadata(str(path)))
                except Exception as e:
                    logger.warning("list_images", f"Failed to get metadata for {path}: {e}")
        return images
