"""
SQLAlchemy Base
모든 ORM 모델이 상속할 Base 클래스
"""
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime
from datetime import datetime

Base = declarative_base()


class TimestampMixin:
    """
    생성/수정 시간 자동 관리 Mixin

    Usage:
        class User(Base, TimestampMixin):
            __tablename__ = "users"
            ...
    """
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
