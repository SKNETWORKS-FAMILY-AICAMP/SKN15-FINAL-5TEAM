"""
Core DB Models

⚠️ DEPRECATED: 이 파일은 더 이상 사용되지 않습니다.
Gemini 피드백에 따라 모델을 feature별로 재구성했습니다:

- User, PasswordResetToken → app/features/auth/models.py
- Session → app/features/sessions/models.py

하위 호환성을 위해 re-export를 제공하지만, 새 코드에서는
각 feature의 models.py를 직접 import하세요.
"""

# ============================================================
# Re-exports for backward compatibility
# ============================================================
# 새 코드에서는 아래 imports를 사용하세요:
# from app.features.auth.models import User, PasswordResetToken
# from app.features.sessions.models import Session

try:
    from app.features.auth.models import User, PasswordResetToken
    from app.features.sessions.models import Session as SessionModel

    # Re-export with deprecation warning
    import warnings
    warnings.warn(
        "Importing models from app.core.db.models is deprecated. "
        "Use app.features.auth.models or app.features.sessions.models instead.",
        DeprecationWarning,
        stacklevel=2
    )

    # For backward compatibility
    Session = SessionModel

except ImportError:
    # Fallback: Import 실패 시 경고
    raise ImportError(
        "Failed to import models from feature modules. "
        "Please ensure app/features/auth/models.py and app/features/sessions/models.py exist."
    )
