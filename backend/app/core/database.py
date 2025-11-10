"""
[Core] 데이터베이스 관련 모듈 편의성 экспо터

이 모듈은 `app.core.db` 하위 모듈에 정의된 주요 데이터베이스 컴포넌트들을
한 곳에서 쉽게 가져올 수 있도록 재내보내기(re-export)하는 역할을 합니다.

이를 통해 다른 모듈에서는 아래와 같이 간결하게 데이터베이스 관련 객체들을
임포트하여 사용할 수 있습니다.

Instead of:
    from app.core.db.session import get_db
    from app.core.db.session import engine

Use:
    from app.core.database import get_db, engine
"""
from app.core.db.session import get_db, get_db_context, AsyncSessionLocal, engine

# __all__ 리스트는 `from app.core.database import *` 구문을 사용할 때
# 외부에 노출할 객체들의 이름을 명시적으로 정의합니다.
__all__ = ["get_db", "get_db_context", "AsyncSessionLocal", "engine"]
