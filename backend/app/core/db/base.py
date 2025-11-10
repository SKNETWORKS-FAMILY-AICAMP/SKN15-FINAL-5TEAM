"""
[Core/DB] SQLAlchemy 모델 기반 정의 모듈

이 모듈은 SQLAlchemy ORM(Object Relational Mapper) 모델의 기반이 되는
`Base` 클래스와 공통으로 사용될 `TimestampMixin`을 정의합니다.
모든 데이터베이스 테이블 모델은 여기서 정의된 `Base`를 상속받아야 합니다.
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime
from datetime import datetime

# ============================================================
# SQLAlchemy Declarative Base
# ============================================================
# declarative_base() 함수는 모든 ORM 모델 클래스가 상속받을 기본 클래스를 생성합니다.
# 이 Base를 통해 SQLAlchemy는 상속받는 모든 클래스들을 탐지하고,
# 해당 클래스들을 데이터베이스 테이블에 매핑하는 메타데이터를 관리합니다.
Base = declarative_base()


# ============================================================
# Timestamp Mixin 클래스
# ============================================================
class TimestampMixin:
    """
    생성 시간(created_at)과 수정 시간(updated_at)을 자동으로 관리하는 Mixin 클래스입니다.

    이 클래스를 ORM 모델에서 상속받으면, 해당 테이블에 `created_at`과 `updated_at`
    컬럼이 자동으로 추가되며, 데이터 생성 및 업데이트 시 시간이 자동으로 기록됩니다.
    이를 통해 코드 중복을 줄이고 모델 정의를 깔끔하게 유지할 수 있습니다.

    Attributes:
        created_at (Column): 데이터가 처음 생성된 시간 (UTC)
        updated_at (Column): 데이터가 마지막으로 수정된 시간 (UTC)

    Usage:
        class YourModel(Base, TimestampMixin):
            __tablename__ = "your_table"
            # ... other columns
    """
    # 데이터 생성 시 현재 UTC 시간으로 기본값 설정
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 데이터 생성 및 업데이트 시 현재 UTC 시간으로 자동 업데이트
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
