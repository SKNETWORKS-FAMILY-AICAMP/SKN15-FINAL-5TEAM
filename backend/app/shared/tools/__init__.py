"""
Shared Tools
공유 도구 클래스

Note:
이 디렉토리는 tm_work 브랜치의 src/tools/ 파일들을 마이그레이션하기 위한 위치입니다.
현재 4-Layer 아키텍처에서는 대부분의 기능이 이미 Services나 Agents에 통합되어 있습니다.

tm_work의 tools 파일들:
- scene_tools.py → app/features/scenarios/services/
- state_tools.py → app/features/chat/services/
- fallback_tools.py → app/features/chat/services/
- image_manager.py → app/features/galleries/services/ (필요시)
- loop_tools.py → app/features/chat/services/ (필요시)
- training_logger.py → app/core/logging.py (이미 통합)

필요한 경우 개별적으로 마이그레이션하세요.
"""
